#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=3
#SBATCH --gres=gpu:2
#SBATCH --time=12:00:00
#SBATCH --mem=128GB
#SBATCH --job-name=TEST_VQ_VAE
#SBATCH --mail-type=END
#SBATCH --mail-user=danielfaronbi@nyu.edu
#SBATCH --output=logs/test_vq_%j.out

singularity exec --nv \
--overlay overlay-50G-10M.ext3:rw /scratch/work/public/singularity/cuda11.6.124-cudnn8.4.0.27-devel-ubuntu20.04.4.sif\
 /bin/bash -c "nvidia-smi; source /ext3/env.sh; conda activate m_gen; python train.py"