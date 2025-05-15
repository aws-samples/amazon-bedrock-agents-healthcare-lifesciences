import argparse
import json
import os
import logging
import boto3
import subprocess
from tqdm import tqdm

import torch
import evo_prot_grad
from transformers import AutoModel, EsmForMaskedLM, AutoTokenizer
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns



logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.INFO,
)

def download_s3_folder(s3_uri, local_dir):
    """
    Download a folder from S3 to a local directory
    """
    # Parse the S3 URI
    if not s3_uri.endswith('/'):
        s3_uri += '/'
    
    bucket_name = s3_uri.split('//')[1].split('/')[0]
    prefix = '/'.join(s3_uri.split('//')[1].split('/')[1:])
    
    logging.info(f"Downloading from bucket: {bucket_name}, prefix: {prefix} to {local_dir}")
    
    # Use AWS CLI for efficient recursive download
    cmd = f"aws s3 cp --recursive s3://{bucket_name}/{prefix} {local_dir}"
    logging.info(f"Running command: {cmd}")
    
    try:
        subprocess.check_call(cmd, shell=True)
        logging.info(f"Successfully downloaded S3 folder to {local_dir}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to download S3 folder: {e}")
        raise

def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "wt_seq", help="Wildtype sequence to evolve", type=str
    )
    parser.add_argument(
        "output_path", help="file path for output files", type=str
    )
    parser.add_argument(
        "--esm_expert_name_or_path",
        help="ESMFold model to use, specify 'None' to skip",
        default="facebook/esm2_t6_8M_UR50D",
        type=str,
    )
    parser.add_argument(
        "--bert_expert_name_or_path",
        help="Bert model to use, specify 'None' to skip",
        default="None",
        type=str,
    )
    parser.add_argument(
        "--scorer_expert_name_or_path",
        help="Scoring model to use, specify 'None' to skip",
        default='None',
        type=str,
    )
    parser.add_argument(
        "--output_type",
        help="Output type, can be 'best', 'last', or 'all' variants",
        default="all",
        type=str,
    )
    parser.add_argument(
        "--parallel_chains",
        help="Number of MCMC chains to run in parallel",
        default=5,
        type=int,
    )
    parser.add_argument(
        "--n_steps",
        help="Number of MCMC steps per chain",
        default=20,
        type=int,
    )
    parser.add_argument(
        "--max_mutations",
        help="maximum number of mutations per variant",
        default=10,
        type=int,
    )
    parser.add_argument('--verbose', 
                        action='store_true', 
                        help='Enable verbose output')
    return parser.parse_known_args()


def get_expert_list(args):
    '''
    Define the chain of experts to run directed evolution with.
    '''
    # Handle S3 paths for ESM model
    if args.esm_expert_name_or_path is not None and args.esm_expert_name_or_path != "None":
        if args.esm_expert_name_or_path.startswith('s3://'):
            # Create a temporary directory for the model
            tmp_dir = os.environ.get('TMPDIR', '/tmp')
            esm_model_dir = os.path.join(tmp_dir, 
                                os.path.basename(os.path.dirname(args.esm_expert_name_or_path.rstrip('/'))))
            if not os.path.exists(esm_model_dir):
                os.makedirs(esm_model_dir, exist_ok=True)
            
            logging.info(f'Downloading ESM model files from {args.esm_expert_name_or_path} to {esm_model_dir}')
            download_s3_folder(args.esm_expert_name_or_path, esm_model_dir)
            logging.info(f'Downloaded files: {os.listdir(esm_model_dir)}')
            
            # Update the path to use the local directory
            args.esm_expert_name_or_path = esm_model_dir
            logging.info(f'Using local ESM model path: {args.esm_expert_name_or_path}')
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logging.info(f"Using device: {device}")
    
    expert_list = []
    assert ((args.esm_expert_name_or_path != 'None') ^ (args.bert_expert_name_or_path != 'None')),\
        "Currently support ONLY ONE generator model (EITHER ESM or Bert) in the expert chain"
    
    if args.esm_expert_name_or_path != "None":
        # Load the ESM-2 model and tokenizer as the expert
        logging.info(f"Loading ESM model from {args.esm_expert_name_or_path}")
        esm2_expert = evo_prot_grad.get_expert(
            'esm',
            model=EsmForMaskedLM.from_pretrained(args.esm_expert_name_or_path, trust_remote_code=True),
            tokenizer=AutoTokenizer.from_pretrained(args.esm_expert_name_or_path, trust_remote_code=True),
            scoring_strategy = 'mutant_marginal',
            temperature=1.0,
            device=device
        )
        expert_list.append(esm2_expert)
    elif args.bert_expert_name_or_path != "None":
        logging.info(f"Loading BERT model from {args.bert_expert_name_or_path}")
        bert_expert = evo_prot_grad.get_expert(
            'bert',
            scoring_strategy='pseudolikelihood_ratio', 
            temperature=1.0,
            model=AutoModel.from_pretrained(args.bert_expert_name_or_path, trust_remote_code=True),
            device=device
        )
        expert_list.append(bert_expert)
    
    if args.scorer_expert_name_or_path != "None":
        logging.info(f"Loading scorer model from {args.scorer_expert_name_or_path}")
        scorer_expert = evo_prot_grad.get_expert(
            'onehot_downstream_regression',
            scoring_strategy='attribute_value',
            temperature=1.0,
            model=AutoModel.from_pretrained(args.scorer_expert_name_or_path, trust_remote_code=True),
            device=device
        )
        expert_list.append(scorer_expert)
    
    return expert_list
        

def run_evo_prot_grad(args):
    '''
    Run the specified expert pipeline on the wildtype sequence to evolve it. 
    '''
    expert_list = get_expert_list(args)
        
    # Initialize Directed Evolution with the specified experts
    directed_evolution = evo_prot_grad.DirectedEvolution(
        wt_protein=args.wt_seq,
        output=args.output_type,
        experts=expert_list,
        parallel_chains=args.parallel_chains,
        n_steps=args.n_steps,
        max_mutations=args.max_mutations,
        verbose=args.verbose                 
    )

    # Run the evolution process
    variants, scores = directed_evolution()

    # Write results to file 
    directed_evolution.save_results(
        csv_filename=os.path.join(args.output_path, "de_results.csv"),
        variants=variants,
        scores=scores,
        n_seqs_to_keep=None, #keep all
        )

if __name__ == "__main__":
    args, _ = _parse_args()
    print(args)
    # Run directed evolution
    run_evo_prot_grad(args)
    print(f"DE results and params saved to {args.output_path}")
