import argparse
import json
import os
import logging
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
        default='NREL/avGFP-fluorescence-onehot-cnn',
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
    device = "cuda" if torch.cuda else "cpu"
    expert_list = []
    assert ((args.esm_expert_name_or_path != 'None') ^ (args.bert_expert_name_or_path != 'None')),\
        "Currently support ONLY ONE generator model (EITHER ESM or Bert) in the expert chain"
    if args.esm_expert_name_or_path != "None":
        # Load the ESM-2 model and tokenizer as the expert
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
        bert_expert = evo_prot_grad.get_expert(
            'bert',
            scoring_strategy='pseudolikelihood_ratio', 
            temperature=1.0,
            model=AutoModel.from_pretrained(args.bert_expert_name_or_path, trust_remote_code=True),
            device=device
        )
        expert_list.append(bert_expert)
    
    if args.scorer_expert_name_or_path != "None":
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
