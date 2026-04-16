#!/usr/bin/env python3
"""
Script to load VCF or GVCF files into the variant_db_3.genomic_variants Iceberg table.
This script parses VCF/GVCF files and loads the data into the Iceberg table created by schema_3.py.
"""

import argparse
import os
import sys
import pyarrow as pa
from pyiceberg.exceptions import NoSuchTableError
from utils import load_s3_tables_catalog, retry_operation
import gzip
import boto3
from io import TextIOWrapper

# Configuration
NAMESPACE = "variant_db_3"
TABLE_NAME = "genomic_variants_fixed"
BATCH_SIZE = 100000  # Number of records to process before writing to the table
MULTI_SAMPLE_BATCH_SIZE = 5000  # Smaller batch for multi-sample VCFs


def parse_s3_uri(s3_uri):
    """Parse S3 URI and return bucket and key.
    
    Args:
        s3_uri (str): S3 URI in format s3://bucket/key
        
    Returns:
        tuple: (bucket, key)
        
    Raises:
        ValueError: If URI is invalid or missing parts
    """
    if not s3_uri.startswith('s3://'):
        raise ValueError(f"Invalid S3 URI format: {s3_uri}. URIs must begin with s3://")
    
    s3_parts = s3_uri[5:].split('/', 1)
    if len(s3_parts) != 2 or not s3_parts[0] or not s3_parts[1]:
        raise ValueError(f"Invalid S3 URI - missing bucket or key: {s3_uri}")
    
    return s3_parts[0], s3_parts[1]


def get_table():
    """Get the existing table or fail if it doesn't exist."""
    # Load the catalog using the utility function
    catalog = load_s3_tables_catalog(bucket_arn)

    # Check if namespace exists
    try:
        namespaces = [ns[0] for ns in catalog.list_namespaces()]
        if NAMESPACE not in namespaces:
            print(f"Error: Namespace '{NAMESPACE}' does not exist.")
            sys.exit(1)
    except Exception as e:
        print(f"Error checking namespaces: {e}")
        sys.exit(1)

    # Check if table exists
    table_identifier = f"{NAMESPACE}.{TABLE_NAME}"
    try:
        return catalog.load_table(table_identifier)
    except NoSuchTableError:
        print(f"Error: Table '{table_identifier}' does not exist.")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading table: {e}")
        sys.exit(1)


def open_vcf_file(file_path):
    """Open a VCF file, handling both local files and S3 URIs, with gzip support.
    
    Uses smart_open for S3 files to enable true streaming without buffering
    the entire object in memory.
    """
    if file_path.startswith('s3://'):
        import smart_open
        return smart_open.open(file_path, 'r')
    else:
        if file_path.endswith('.gz'):
            return gzip.open(file_path, 'rt')
        else:
            return open(file_path, 'r', encoding='utf-8')


def parse_vcf_header(vcf_file):
    """Parse the VCF header to extract format and sample information."""
    samples = []
    info_fields = {}
    format_fields = {}

    for line in vcf_file:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # End of header
        if line.startswith('#CHROM'):
            # Extract sample names from the header line
            header_fields = line.split('\t')
            if len(header_fields) > 9:  # VCF has samples
                samples = header_fields[9:]
            break

        # Parse INFO field definitions
        elif line.startswith('##INFO='):
            info_def = line[8:-1]  # Remove ##INFO=< and >
            info_parts = info_def.split(',', 3)
            info_id = info_parts[0].split('=')[1]
            info_fields[info_id] = {
                'id': info_id,
                'type': info_parts[2].split('=')[1]
            }

        # Parse FORMAT field definitions
        elif line.startswith('##FORMAT='):
            format_def = line[10:-1]  # Remove ##FORMAT=< and >
            format_parts = format_def.split(',', 3)
            format_id = format_parts[0].split('=')[1]
            format_fields[format_id] = {
                'id': format_id,
                'type': format_parts[2].split('=')[1]
            }

    return samples, info_fields, format_fields


def parse_info_field(info_str):
    """Parse the INFO field from a VCF record."""
    if info_str == '.':
        return {}

    info_dict = {}
    for item in info_str.split(';'):
        if '=' in item:
            key, value = item.split('=', 1)
            info_dict[key] = value
        else:
            info_dict[item] = 'true'

    return info_dict


def parse_format_field(format_str, sample_str):
    """Parse the FORMAT and sample fields from a VCF record."""
    if format_str == '.' or sample_str == '.':
        return {}

    format_keys = format_str.split(':')
    sample_values = sample_str.split(':')

    # Handle cases where sample values might be missing
    if len(sample_values) < len(format_keys):
        sample_values.extend(['.' for _ in range(len(format_keys) - len(sample_values))])

    return dict(zip(format_keys, sample_values))


def process_vcf_batch_single_sample(batch_records, sample_name, sample_idx):
    """Process a batch of VCF records for a single sample. Memory-efficient."""
    n = len(batch_records)
    sample_name_list = [sample_name] * n
    variant_name_list = []
    chrom_list = []
    pos_list = []
    ref_list = []
    alt_list = []
    qual_list = []
    filter_list = []
    genotype_list = []
    info_list = []
    attributes_list = []
    is_reference_block_list = []

    for fields in batch_records:
        chrom_list.append(fields[0])
        pos_list.append(int(fields[1]))
        variant_name_list.append(fields[2])
        ref_list.append(fields[3])
        alt_list.append([a if a != '.' else '' for a in fields[4].split(',')])

        qual = None
        if fields[5] != '.':
            try:
                qual = float(fields[5])
            except ValueError:
                pass
        qual_list.append(qual)

        filter_val = fields[6] if fields[6] != '.' else None
        filter_list.append(filter_val)

        info_dict = parse_info_field(fields[7])
        info_list.append(info_dict)
        is_reference_block_list.append('END' in info_dict)

        if len(fields) > 9 + sample_idx:
            attributes = parse_format_field(fields[8], fields[9 + sample_idx])
            genotype_list.append(attributes.get('GT', './.'))
            attributes_list.append(attributes)
        else:
            genotype_list.append('./.')
            attributes_list.append({})

    return {
        'sample_name': pa.array(sample_name_list, type=pa.string()),
        'variant_name': pa.array(variant_name_list, type=pa.string()),
        'chrom': pa.array(chrom_list, type=pa.string()),
        'pos': pa.array(pos_list, type=pa.int64()),
        'ref': pa.array(ref_list, type=pa.string()),
        'alt': pa.array(alt_list, type=pa.list_(pa.string())),
        'qual': pa.array(qual_list, type=pa.float64()),
        'filter': pa.array(filter_list, type=pa.string()),
        'genotype': pa.array(genotype_list, type=pa.string()),
        'info': pa.array([{str(k): str(v) for k, v in d.items()} for d in info_list],
                         type=pa.map_(pa.string(), pa.string())),
        'attributes': pa.array([{str(k): str(v) for k, v in d.items()} for d in attributes_list],
                               type=pa.map_(pa.string(), pa.string())),
        'is_reference_block': pa.array(is_reference_block_list, type=pa.bool_()),
    }


def process_vcf_file(vcf_path, sample_name=None, table=None, pyarrow_schema=None):
    """Process a VCF file streaming in chunks, one sample at a time per chunk.
    
    Reads VCF lines in small chunks. For each chunk, iterates over samples
    and writes each sample's data to Iceberg before moving to the next sample.
    This keeps memory proportional to chunk_size (not chunk_size × num_samples).
    """
    print(f"Processing VCF file: {vcf_path}")

    with open_vcf_file(vcf_path) as vcf_file:
        samples, info_fields, format_fields = parse_vcf_header(vcf_file)

        if sample_name:
            if sample_name in samples:
                target_samples = [(samples.index(sample_name), sample_name)]
            else:
                print(f"Warning: Sample '{sample_name}' not found. Using first: {samples[0] if samples else 'N/A'}")
                target_samples = [(0, samples[0])] if samples else []
        elif samples:
            target_samples = list(enumerate(samples))
        else:
            name = os.path.basename(vcf_path).split('.')[0]
            target_samples = [(0, name)]

        num_samples = len(target_samples)
        num_columns = len(samples)  # total columns in VCF (drives per-line memory)
        chunk_size = max(10000, BATCH_SIZE // max(num_columns, 1))
        print(f"Will process {num_samples} sample(s) from {num_columns}-column VCF, chunk_size={chunk_size}")

        total_lines = 0
        chunk = []

        for line in vcf_file:
            if line.startswith('#'):
                continue
            fields = line.strip().split('\t')
            if len(fields) < 8:
                continue
            chunk.append(fields)

            if len(chunk) >= chunk_size:
                _flush_chunk(chunk, target_samples, table, pyarrow_schema)
                total_lines += len(chunk)
                print(f"  Lines processed: {total_lines}")
                chunk = []

        if chunk:
            _flush_chunk(chunk, target_samples, table, pyarrow_schema)
            total_lines += len(chunk)

    total_records = total_lines * num_samples
    print(f"Done: {total_lines} VCF lines × {num_samples} samples = {total_records} records")
    return None


def _flush_chunk(chunk, target_samples, table, pyarrow_schema):
    """Write one chunk of VCF lines to Iceberg, one sample at a time."""
    for sample_idx, sname in target_samples:
        data_arrays = process_vcf_batch_single_sample(chunk, sname, sample_idx)
        if table and pyarrow_schema:
            write_to_iceberg(table, data_arrays, pyarrow_schema)
        del data_arrays


def write_to_iceberg(table, data_arrays, pyarrow_schema):
    """Write data to the Iceberg table, refreshing metadata to avoid stale commits."""
    arrow_table = pa.Table.from_arrays([
        data_arrays['sample_name'],
        data_arrays['variant_name'],
        data_arrays['chrom'],
        data_arrays['pos'],
        data_arrays['ref'],
        data_arrays['alt'],
        data_arrays['qual'],
        data_arrays['filter'],
        data_arrays['genotype'],
        data_arrays['info'],
        data_arrays['attributes'],
        data_arrays['is_reference_block']
    ], schema=pyarrow_schema)

    print(f"Writing {len(arrow_table)} rows to Iceberg table...")

    import time
    for attempt in range(10):
        try:
            table.refresh()
            table.append(arrow_table)
            print(f"Successfully wrote {len(arrow_table)} rows to {NAMESPACE}.{TABLE_NAME}")
            return
        except Exception as e:
            err_str = str(e).lower()
            if ("commit" in err_str and ("conflict" in err_str or "failed" in err_str or "changed" in err_str)) and attempt < 9:
                wait = (attempt + 1) * 2
                print(f"Commit conflict, retry {attempt + 1}/10 in {wait}s: {e}")
                time.sleep(wait)
            else:
                raise


def main():
    """Main function to load VCF/GVCF data into the Iceberg table."""
    global bucket_arn, NAMESPACE, TABLE_NAME, BATCH_SIZE

    parser = argparse.ArgumentParser(description='Load VCF/GVCF files into Iceberg table')
    parser.add_argument('vcf_files', nargs='+', help='VCF or GVCF file paths to load')
    parser.add_argument('--sample', help='Sample name to use (overrides sample names in VCF)')
    parser.add_argument('--bucket-arn', required=True, help='S3Tables bucket ARN')
    parser.add_argument('--namespace', default=NAMESPACE, help=f'Iceberg namespace (default: {NAMESPACE})')
    parser.add_argument('--table', default=TABLE_NAME, help=f'Iceberg table name (default: {TABLE_NAME})')
    parser.add_argument('--batch-size', type=int, default=BATCH_SIZE,
                        help=f'Number of records to process from each sample before writing (default: {BATCH_SIZE})')

    args = parser.parse_args()
    bucket_arn = args.bucket_arn
    NAMESPACE = args.namespace
    TABLE_NAME = args.table
    BATCH_SIZE = args.batch_size

    print("Getting table...")
    table = get_table()
    pyarrow_schema = table.schema().as_arrow()

    # Process each VCF file
    for vcf_file in args.vcf_files:
        # Check file existence for both local and S3 files
        file_exists = True
        if vcf_file.startswith('s3://'):
            try:
                bucket, key = parse_s3_uri(vcf_file)
                s3_client = boto3.client('s3')
                s3_client.head_object(Bucket=bucket, Key=key)
            except Exception as e:
                file_exists = False
                print(f"Error: S3 file not found: {vcf_file} - {e}")
        else:
            file_exists = os.path.exists(vcf_file)
            if not file_exists:
                print(f"Error: Local file not found: {vcf_file}")
        
        if not file_exists:
            continue

        try:
            # Process the file in batches and write directly to the table
            process_vcf_file(vcf_file, args.sample, table, pyarrow_schema)
        except Exception as e:
            print(f"Error processing file {vcf_file}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
