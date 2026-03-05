# AI-Assisted Writing Is Growing Fastest Among Non-English-Speaking and Less Established Scientists
* by Jialin Liu, Yongyuan He, Zhihan Zheng, Yi Bu, Chaoqun Ni

This repository stores related data and codes for the paper **"AI-Assisted Writing Is Growing Fastest Among Non-English-Speaking and Less Established Scientists"**.

---

### System Requirements

**Operating System:** This code has been tested on Windows 11. It should be compatible with any standard operating system that supports Python.

**Software:**
* Python [3.8+] 
* Jupyter Notebook or JupyterLab

**Hardware:**
Standard computer. No special hardware (e.g., GPU, high-memory server) is required to run the visualization code.

---

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/MetascienceLab/aiwriting
   ```
2. Install the required dependencies. 
   ```bash
   pip install -r requirements.txt
   ```

---

### Instructions for Use

1. Launch Jupyter Notebook in the repository directory:
   ```bash
   jupyter notebook
   ```
2. Open the `aiwriting_visualization.ipynb` file.
3. Run all cells in the notebook.

**Expected Output:** The notebook will read the CSV files in the repository and generate the main and supplementary figures presented in the manuscript.

*Typical run time: Approximately 10 minutes.*

---

### Main Files
* `aiwriting_visualization.ipynb`: Jupyter notebook containing all visualization code

### Data Files
* `aiwriting_data.csv`: Main dataset containing AI-generated content scores, author information, acceptance dates, etc.
* `data_figure2.csv`: Data for Figure 2
* `data_figure_s1.csv`: Data for Figure S1
* `data_figure_s3_s4_s5.csv`: Data for Figures S3-S5
* `data_figure_s7.csv`: Data for Figure S7
* `data_figure_s8.csv`: Data for Figure S8
* `first_author_data.csv`: First author analysis data
* `corresponding_author_data.csv`: Corresponding author analysis data
* `country_epi.txt`: Country-level English Proficiency Index (EPI) data
* `country_language_type.txt`: Country language type classification data

---

### License
This project is covered under the **MIT License**. Please see the `LICENSE` file for more details.

### Citation
If you find this data and code useful for your research, please cite our paper:
```bibtex
@article{liu2025ai,
  title={AI-assisted writing is growing fastest among non-english-speaking and less established scientists},
  author={Liu, Jialin and He, Yongyuan and Zheng, Zhihan and Bu, Yi and Ni, Chaoqun},
  journal={arXiv preprint arXiv:2511.15872},
  year={2025}
}
```
