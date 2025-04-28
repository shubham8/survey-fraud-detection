# **Fraud Detection Method**

- [Before you begin](#before-you-begin)
- [Set up parameters](#set-up-parameters)
  - [Sheet 1: `filepaths`](#sheet-1-filepaths)
  - [Sheet 2: `flags`](#sheet-2-flags)
  - [Sheet 3: `initial_classification_rules`](#sheet-3-initial_classification_rules)
  - [Sheet 4: `final_classification_rules`](#sheet-4-final_classification_rules)
- [Fraud detection](#fraud-detection)
  - [Step 1: Initial classification](#step-1-initial-classification)
  - [Step 2: Get descriptive statistics and generate plots (Optional)](#step-2-get-descriptive-statistics-and-generate-plots-optional)
  - [Step 3: Manual classification](#step-3-manual-classification)
  - [Step 4: Final classification](#step-4-final-classification)
  - [Step 5: Get descriptive statistics and generate plots (Optional)](#step-5-get-descriptive-statistics-and-generate-plots-optional)
- [Optional Tool: Fuzzy String Matching Tool](#optional-tool-fuzzy-string-matching-tool)
  - [Sheet 5: `fuzzy_string`](#sheet-5-fuzzy_string)

# Before you begin

- Verify the folder structure
```text
.
├── config/
    ├── parameters.xlsx # Parameters file. Requires user input.
    └── world-administrative-boundaries # Optional shape file to get country from latitude-longitude
        ├── world-administrative-boundaries.cpg
        ├── world-administrative-boundaries.dbf
        ├── world-administrative-boundaries.prj
        ├── world-administrative-boundaries.shp # Shape file. File path in parameters.xlsx.
        ├── world-administrative-boundaries.shx
        └── world-administrative-boundaries-countries.txt # List of country names
├── data/ # Data folder for base files and generated files. 
    └── sample_data.csv
├── 01_initial_classification.py
├── 02_get_initial_descriptives.py
├── 04_final_classification.py
├── 05_get_final_descriptives.py
├── README.md
└── fraud_detection.py # Contains implemented methods.
```
- Install [Python-3.12.9](https://www.python.org/downloads/release/python-3129/). Newer verions may work as well.

*For Windows users:*
- Open command prompt 
- [Optional] Set up a virtual environment to avoid version conflicts.
    - Navigate to the project folder: `cd \path\to\spam-detection`
    - Create a virtual environment: `python -m venv myvenv` 
    - Activate the virtual environment: `myvenv\Scripts\activate`
- Install required Python modules: `pip install -r \path\to\requirements.txt`


# Set up parameters

- Ensure that `parameters.xlsx` exists in the `config` folder. This file should contain the following four sheets:

## Sheet 1: `filepaths`
Specifies paths for files and folder. This sheet contains three columns:

- 🚫 **[DO NOT EDIT]** `parameter`: Variable names used to refer specific file or folder. 

- ✏️ **[EDIT / REVIEW]** `value`: Path of corresponding `parameter`. The `value` for the `data_file` parameter must be changed to the survey data filepath.

- 🔧 **[OPTIONAL EDIT]** `description`: Description of corresponding `parameter`.

## Sheet 2: `flags`
Contains details of flags used for automated fraud detection. Each row specifies one flag. This sheet contains six columns:

- 🔧 **[OPTIONAL EDIT]** `flag_name`: Name of the flag. We recommend using the convention `F_FlagName`.

- 🔧 **[OPTIONAL EDIT]** `method_name` Name of the method used. Must match the method name implemented in `fraud_detection.py`. See `docs` for more details.

- 🔧 **[OPTIONAL EDIT]** `flag_group`: Name of the flag group. We recommend using the convention `FG_FlagGroupName`.

- ✏️ **[EDIT / REVIEW]** `use_flag`: Indicator for using the flag (`1`) or not (`0`). 

- ✏️ **[EDIT / REVIEW]** `parameters`: Flag-specific paramters that are required by the corresponding method. See `docs` for more details.

- 🔧 **[OPTIONAL EDIT]** `description`: A brief description of the flag. Optional.

## Sheet 3: `initial_classification_rules`
Contains a sequence of top-down rules to classify responses based on flag groups. Once a rule is satisfied, the response is assigned the corresponding classification, and no subsequent rules are evaluated. This sheet contains four columns:

- 🔧 **[OPTIONAL EDIT]** `rule_num`: Rule number. Optional.

- 🔧 **[OPTIONAL EDIT]** `condition_expr`: An expression for the Boolean condition using flag groups. The expression is evaluated using Python's [`eval()`](https://docs.python.org/3/library/functions.html#eval). The evaluation of the expression must return either `True` or `False`.

- 🔧 **[OPTIONAL EDIT]** `classification`: Response classification label.

- 🔧 **[OPTIONAL EDIT]** `use_rule`: Indicator for using the rule (`1`) or not (`0`).

## Sheet 4: `final_classification_rules`
Contains a sequence of top-down rules to classify responses combining automated and manual classification. Once a rule is satisfied, the response is assigned the corresponding classification, and no subsequent rules are evaluated. This sheet contains four columns:

- 🔧 **[OPTIONAL EDIT]** `rule_num`: Rule number. Optional.

- 🔧 **[OPTIONAL EDIT]** `condition_expr`: An expression for the Boolean condition using `FLAG` and `MANUAL_FLAG` columns. The expression is evaluated using Python's [`eval()`](https://docs.python.org/3/library/functions.html#eval). The evaluation of the expression must return either `True` or `False`.

- 🔧 **[OPTIONAL EDIT]** `classification`: Response classification label.

- 🔧 **[OPTIONAL EDIT]** `use_rule`: Indicator for using the rule (`1`) or not (`0`).


# Fraud detection

❗ **IMPORTANT: We strongly recommend executing the scripts via the command line**. 

*For Windows users:*
- Open command prompt (Windows)
  - Navigate to the project folder: `cd \path\to\spam-detection`
  - Execute the script: `python script_name.py` (e.g., `python 02_get_initial_descriptives.py`)

## Step 1: Initial classification
Execute `01_initial_classification.py` to generate an output file with automated response classification. 

The output file path is the value of `flagged_file` in the `filepaths` sheet of `parameters.xlsx`. The output file will contain:

- The original survey data columns.
- Columns corresponding to each flag indicating TRUE or FLASE. Some additional columns corresponding to specific methods may also be created.
- Columns corresponding to each flag group with the number of corresponding flags activated.
- The automated response classification column `FLAG`.
- Placeholder columns for manual classification by the user `MANUAL_FLAG` and `MANUAL_COMMENT`.

## Step 2: Get descriptive statistics and generate plots (Optional)
Execute `02_get_initial_descriptives.py` to print descriptive statistics (such as counts) for the flags and flag groups and to generate co-occurence plots for diagnostic purposes. 

- If provided, the plots are saved in the `figure_folder` folder provided in the `filepaths` sheet of `parameters.xlsx`. 

## Step 3: Manual classification
This step involves user to manually classify the responses, especially the ones marked as `TBD` in the `FLAG` column during automated classification. 

Manual classification can be done in the `flagged_file` itself. However, a `manual_file` path can be set in the `filepaths` sheet of `parameters.xlsx` if the file is copied before manual classification.

- The `MANUAL_FLAG` entered by the user are used to evaluate the `condition_expr` in the `final_classification_rules` sheet of `parameters.xlsx`. 
- `MANUAL_COMMENT` is an optional column to add information justfying the manual classification.

## Step 4: Final classification
Execute `04_final_classification.py` to generate an output file that combines automated and manual classifications.

The output file path is the value of `final_output_file` in the `filepaths` sheet of `parameters.xlsx`. The output file will contain:

- All columns in `manual_file`.
- A final classification column `FINAL_FLAG`.

## Step 5: Get descriptive statistics and generate plots (Optional)
Execute `05_get_final_descriptives.py` to print descriptive statistics (such as counts) for the flags and flag groups and to generate co-occurence plots for diagnostic purposes. 

If `figure_folder` value provided in the `filepaths` sheet of `parameters.xlsx`, the plots are saved in the `figure_folder` folder. 


# Optional Tool: Fuzzy String Matching Tool

This fuzzy string matching tool compares each text responses within a column and computes a similarity score (ranging from 0 and 100) based on the presence and frequency of shared words. Two columns are added to the dataframe: 

- `FZ_COUNT_{column}`: Number of similar responses(score > set threshold), and 
- `FZ_SIMILAR_{column}`: Score and text of similar responses. 

This tool is particularly useful for larger samples as it provides an easy reference for closer inspection during manual review; however, execution may be slow. It can also be implemented as a custom flag. 

To use this tool, 

- Install `rapidfuzz` v3.13 module using: `pip install rapidfuzz==3.13.0`
- Verify that `fuzzy_string` sheet exists in `parameters.xlsx`. 
- Verify that a value for the paramter `fuzzy_file` is provided in the `filepaths` sheet in `parameters.xlsx`. 
  - If using this tool with automated response classification, set `fuzzy_file` same as `data_file` and run the `tool_mark_similar_responses.py` before `01_initial_classification.py`.
  - If using this tool after automated response classification but before manual classification, set `fuzzy_file` same as `flagged_file` and run the `tool_mark_similar_responses.py` before manually classifying the data.
  
## Sheet 5: `fuzzy_string`
Contains information about text-response columns on which fuzzy string algorithm should be applied. Each row specifies one text-response column. This sheet contains six columns:

- ✏️ **[EDIT / REVIEW]**  `column`: Data column name to check for similar resppnses.

- 🔧 **[OPTIONAL EDIT]** `minimum_length`: The minimum number of characters a text response should have to be tested for similarity. Responses having lesser number of characters will be ignored. This is useful to ignore comparing common short and valid responses like "Nothing", "None", or any context-dependent short responses. 

- 🚫 **[DO NOT EDIT]** `fuzzy_algorithm`: Fuzzy string matching llgorithm used for comparing responses. We recommend using `token_sort_ratio` as it considers both the presence and the frequency of words. For more details, please see the [`rapidfuzz` documentation](https://rapidfuzz.github.io/RapidFuzz/Usage/fuzz.html).

- 🔧 **[OPTIONAL EDIT]** `threshold`: Threshold to mark similar responses. Defaults to 65. This should be changed based on trial and error. 