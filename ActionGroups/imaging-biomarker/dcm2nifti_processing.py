#!/usr/bin/env python
import argparse
import dcmstack
from glob import glob
import pydicom
import nibabel as nib
import numpy as np
import sys
import os
import json
import time
import logging
from nilearn import plotting
import matplotlib.pyplot as plt
import radiomics_utils as utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--subject', type=str, default='R01-003',
                        help='Subject ID (default: R01-003)')
    parser.add_argument('--feature_store_name', type=str, default='nsclc-radiogenomics-imaging-feature-group',
                        help='SageMaker Feature Store Group Name (default: nsclc-radiogenomics-imaging-feature-group)')
    parser.add_argument('--offline_store_s3uri', type=str,
                        help='SageMaker Feature Offline Store S3 URI Example: s3://multimodal-image-data-processed/nsclc-radiogenomics-multimodal-imaging-featurestore.')
    
    args = parser.parse_args()
    
    data_dir = '/opt/ml/processing/input/'
    output_dir = '/opt/ml/processing/output/'

    # assume one subject comes in,
    # we need to find out where the CT dicom files are
    # and segmentation file
    logger.info('Locating DICOM files')
    jsons = glob(os.path.join(data_dir, '*', '*', '*.json'))
    logger.info('%d jsons found.' % len(jsons))
    print('%d jsons found.' % len(jsons))

    valid_jsons = []
    file_info = []
    seg_string = ['3D Slicer segmentation result', 'ePAD Generated DSO']
    for i, jsonfile in enumerate(jsons):
        with open(jsonfile) as f:
            aa = json.load(f)
            if seg_string[0].lower() in aa['Total'][-1].lower() or seg_string[1].lower() in aa['Total'][-1].lower():
                logger.debug(aa['Total'][-3:])
                print(aa['Total'][-3:])
                valid_jsons.append(jsonfile)
                file_info.append([aa['StudyUID'], aa['Date'], aa['SeriesUID'], jsonfile])

    if len(valid_jsons) > 1:
        raise Exception('there are more than one segmentation for this patient')

    print(file_info)
    
    src_dcms = glob(os.path.join(data_dir, file_info[0][0], file_info[0][1], '*', '*dcm'))
    src_seg_dcm = [i for i in src_dcms if file_info[0][2] in i]
    logging.info(src_seg_dcm)
    src_dcms.remove(src_seg_dcm[0])
    #print(src_dcms)
    print('# of src_dcms: %d' % len(src_dcms))
    print('# of src_seg_dcm: %d' % len(src_seg_dcm))

    # work with CT scan and load as a Nifti image
    logger.info('Creating nifti images from DICOM files')
    stacks = dcmstack.parse_and_stack(src_dcms)
    stack = list(stacks.values())[0]
    nii = stack.to_nifti()
    img = nii.get_fdata()

    # work with CT segmentation file, load as a numpy array and create a Nifti image
    dcm = pydicom.dcmread(src_seg_dcm[0])
    n_frames_seg = int(dcm.NumberOfFrames)
    seg = dcm.pixel_array
    # reorient the seg array
    seg = np.fliplr(seg.T)
    
    # if seg and img don't have the same dimension, pad the images
    if img.shape != seg.shape:
        # read all dicoms and parse out the instance number and slice location
        # assuming the files are from R01-098 onwards with ePAD Generated DSO
        d_sort_instance_number=[]
        for tmp_dcm_fname in src_dcms:
            tmp_dcm = pydicom.dcmread(tmp_dcm_fname)
            d_sort_instance_number.append((int(tmp_dcm[0x0020, 0x0013].value), tmp_dcm[0x0020, 0x0032].value))
        d_sort_instance_number = sorted(d_sort_instance_number, key=lambda aa: aa[0])
        
        patient_img_position_first = dcm[0x5200, 0x9230][0][0x0020, 0x9113][0]['ImagePositionPatient'].value
        patient_img_position_last = dcm[0x5200, 0x9230][-1][0x0020, 0x9113][0]['ImagePositionPatient'].value
        
        slice_instance_number_1 = [i for i, j in d_sort_instance_number if j == patient_img_position_first][0]
        slice_instance_number_2 = [i for i, j in d_sort_instance_number if j == patient_img_position_last][0]
        top_slice_instance_number = min(slice_instance_number_1, slice_instance_number_2)

#     logger.debug(np.nonzero(seg.sum(axis=1).sum(axis=1))[0])
        tmp_seg = np.zeros_like(img)
        starting_index = img.shape[-1] - top_slice_instance_number - n_frames_seg # the seg and the image is flipped and need to locate from bottom.
        ending_index = starting_index + n_frames_seg
        tmp_seg[:, :, starting_index:ending_index] = seg
        seg = tmp_seg
    seg_nii = nib.Nifti1Image(seg, nii.affine, header = nii.header)

    # save some viz
    logger.info('Saving files.')
    prefix = '%s' % (args.subject)
    f1 = plt.figure(figsize=(16,6))
    g1 = plotting.plot_roi(seg_nii, bg_img = nii, figure = f1, alpha = 0.4, title = 'Lung CT with segmentation')
    g1.savefig(os.path.join(output_dir, 'PNG', '%s_ortho-view.png' % prefix), dpi = 150)

    f2 = plt.figure(figsize=(16,6))
    g2 = plotting.plot_roi(seg_nii, bg_img = nii, figure = f2, alpha = 0.4, title = 'Lung CT with segmentation', 
                           display_mode='z', cut_coords=4)
    g2.savefig(os.path.join(output_dir, 'PNG', '%s_z-view.png' % prefix), dpi = 150)

    # save images
    imageName = os.path.join(output_dir, 'CT-Nifti', '%s.nii.gz' % prefix)
    maskName = os.path.join(output_dir, 'CT-SEG', '%s.nii.gz' % prefix)
    nii.to_filename(imageName)
    seg_nii.to_filename(maskName)
    
    # compute radiomic features
    logging.info('Computing radiomic features')
    df = utils.compute_features(imageName, maskName)
    
    # format dataframe for redshift
    record_id_column = 'Subject'
    event_time_column = 'EventTime'
    df[record_id_column] = args.subject
    current_time_sec = float(round(time.time()))
    df[event_time_column] = current_time_sec
    df['ScanDate'] = file_info[0][1]
    utils.cast_object_to_string(df)
    os.makedirs(os.path.join(output_dir, 'CSV'), exist_ok=True)  
    df.to_csv(os.path.join(output_dir, 'CSV', '%s.csv' % prefix))
    # # check if feature store exists
    # feature_group = utils.check_feature_group(args.feature_store_name)
    # if not feature_group:
    #     feature_group = utils.create_feature_group(args.feature_store_name, df, args.offline_store_s3uri,
    #                                                record_id = record_id_column, event_time = event_time_column, 
    #                                                enable_online_store = True)

    # # ingest features into a FeatureStore
    # feature_group.ingest(data_frame=df, max_workers=1, wait=True)
    
    print('Processing done for %s' % prefix)
    logging.info('Processing done for %s' % prefix)
