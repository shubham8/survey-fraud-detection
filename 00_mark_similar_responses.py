# Implement fuzzy-string
import os
import sys
import numpy as np
import pandas as pd
import itertools
from fraud_detection import filepaths, read_parameters_sheet
from rapidfuzz import fuzz
import traceback
# Adds an exit prompt if an error is raised
sys.excepthook = lambda exc_type, exc_value, tb: (
    traceback.print_exception(exc_type, exc_value, tb),
    input("\nPress Enter to exit...")
)

def get_fuzzy_scores(df, column_name, min_length=7, fuzz_func='token_sort_ratio', 
                          threshold=65, save_matrix=None):
    """
    Adds a column with repsonses having high fuzzy similarity scores
        
    Parameters: 
        df (pd.DataFrame) : Dataframe with relevant text column.
        column_name (str) : Column name with text responses to check.
        min_length (int) : Minimum length of text response to check.
        fuzz_func (str) : Function to implement for search strategy. Defaults to 'token_sort_ratio'.
        threshold (int) : Score threshold to consider a response similar. 
        save_matrix (str) : Optional file path to save similarity matrix.

    Returns:
        df (pd.DataFrame) : Dataframe with added column for similar responses. 
        similarity_matrix (np.array) : Saved a similarity scores in a matrix format.
    """
    
    
    ## Initialization
    texts = df[column_name].fillna('').to_list() # fill NaNs for fuzzy
    N = len(texts)
    fuzz_func = eval(f"fuzz.{fuzz_func}")
    
    ## Calculate similarity matrix
    similarity_matrix = np.zeros((N, N), dtype=int)
    for i, j in itertools.combinations(df.index, 2):
        # Check only those response that are longer than min_length
        if len(texts[i].strip()) >= min_length or len(texts[j].strip()) >= min_length:
            score = int(fuzz_func(texts[i], texts[j]))
            similarity_matrix[i, j] = score
            similarity_matrix[j, i] = score
    
    ## Add count of similar responses that meet the threshold
    df[f'FZ_COUNT_{column_name}'] = (similarity_matrix >= threshold).sum(axis=1)
    
    ## Add similar response texts that meet the threshold 
    similar_matches = pd.Series([[] for _ in range(N)], index=df.index)
    for i in df.index:
        for j in df.index:
            score = similarity_matrix[i, j]
            if score >= threshold:
                similar_matches[i].append(f'{j}. ({score}) "{texts[j]}"')

    df[f'FZ_SIMILAR_{column_name}'] = similar_matches.apply('; '.join)
    df[f'FZ_SIMILAR_{column_name}'] = (
        df[f'FZ_SIMILAR_{column_name}']
        .replace('', np.nan)
        .infer_objects(copy=False)
    )
    
    ## Save similarity matrix
    if isinstance(save_matrix, str):
        if not save_matrix.endswith(".csv"):
            raise ValueError("The file path should be a CSV file.")
        pd.DataFrame(similarity_matrix).to_csv(save_matrix, index=True) 

    return df

if __name__ == "__main__":
    ## Verify and read data
    # Survey data ("data_file")
    var_data = "data_file"
    if var_data not in filepaths['parameter'].values:
        raise KeyError(f"Data file path not found in the parameters file: '{var_data}'.")
    fn_data = filepaths.loc[filepaths['parameter'] == var_data, 'value'].values[0]

    ## Fuzzy algorithm
    print("This method uses fuzzy string matching algorithm. This may take a long time to execute depending on the sample size.")
    print("To run this algorithm, configure the 'fuzzy_string' sheet in the parameters file.")
    
    # Confirm execution
    input_fuzzy = input("\nDo you want to run the fuzzy string matching algorithm? (y/n)") or "n"
    print(input_fuzzy.lower())
    if input_fuzzy.lower() != "y" and input_fuzzy.lower() != "yes":
        print("You chose to not run the fuzzy string algorithm. The file will close now.")
        input("\nPress Enter to exit...")
        sys.exit()

    # Fuzzy file ("fuzzy_file")
    var_data = "fuzzy_file"
    if var_data not in filepaths['parameter'].values:
        raise KeyError(f"Data file path not found in the parameters file: '{var_data}'.")
    fn_fuzz = filepaths.loc[filepaths['parameter'] == var_data, 'value'].values[0]
    # Read data
    df = pd.read_csv(fn_data, low_memory=False) 

    # Read fuzzy params
    params = read_parameters_sheet(sheet_name="fuzzy_string")

    for _, row in params.iterrows():
        print(f"Executing fuzzy string matching for: {row['column']}")
        df = df.pipe(
            get_fuzzy_scores,
            column_name=row['column'], 
            min_length=row['minimum_length'] if row['minimum_length'] else 7, 
            fuzz_func=row['fuzzy_algorithm'] if row['fuzzy_algorithm'] else 'token_sort_ratio', 
            threshold=row['threshold'] if row['threshold'] else 65, 
            save_matrix=row['maxtrix_filepath']
        )

    df.to_csv(fn_fuzz, index=False)

    input("\nPress Enter to exit...")