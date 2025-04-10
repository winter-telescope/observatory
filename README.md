# WINTER Code Repository

This is a code repository for the WINTER observatory. It should include all the control code to run the robotic observatory, as well as the scheduler.

This repository is separate from the instrument development repository.


## Getting environment set up

Try this:

1. conda update -n base -c defaults conda
2. go to top level `observatory` directory
3. Make a new conda environment in this directory: `conda create --prefix .conda python=3.9`
4. Activate the new environment in this directory: `conda activate ./.conda`
5. Update pip: `pip install --upgrade pip`
6. Install dependencies: `pip install -e .` Alternately if you want to install the dev dependencies: `pip install -e ".[dev]"`