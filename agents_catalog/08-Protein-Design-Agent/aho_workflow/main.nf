nextflow.enable.dsl = 2

// static data files are in nextflow.config
workflow {
    def esm_model_ch = params.esm_model_files ? Channel.value(params.esm_model_files) : Channel.value(file('null_esm'))
    def onehotcnn_ch = params.onehotcnn_model_files ? Channel.value(params.onehotcnn_model_files) : Channel.value(file('null_onehotcnn'))

    RunDirectedEvolution(
        params.seed_sequence,
        esm_model_ch,
        onehotcnn_ch,
        params.output_type,
        params.parallel_chains,
        params.n_steps,
        params.max_mutations
    )

}


process RunDirectedEvolution {
    container "${params.container_image}"
    cpus 8
    memory '30 GB'
    accelerator 1, type: 'nvidia-tesla-a10g'
    publishDir '/mnt/workflow/pubdir/de'

    input:
        val seed_sequence
        path esm_model_files
        path onehotcnn_model_files
        val output_type
        val parallel_chains
        val n_steps
        val max_mutations

    output:
        path 'output/*.csv', emit: csvs

    script:
    def esm_arg = esm_model_files.name != 'null_esm' ? "--esm_expert_name_or_path=${esm_model_files}" : ''
    def onehotcnn_arg = onehotcnn_model_files.name != 'null_onehotcnn' ? "--scorer_expert_name_or_path=${onehotcnn_model_files}" : ''
    
    """
    set -euxo pipefail
    mkdir -p output
    
    /opt/conda/bin/python /home/scripts/directed_evolution.py ${seed_sequence} \
        output/ \
        ${esm_arg} \
        ${onehotcnn_arg} \
        --output_type ${output_type} \
        --parallel_chains ${parallel_chains} \
        --n_steps ${n_steps} \
        --max_mutations ${max_mutations}
    """
}