import os
import numpy as np
import pandas as pd
import fraud_detection
from fraud_detection import filepaths

if __name__ == "__main__":
    ## Verify and read data
    # Survey data ("data_file")
    var_data = "data_file"
    if var_data not in filepaths['parameter'].values:
        raise KeyError(f"Data file path not found in the parameters file: '{var_data}'.")
    fn_data = filepaths.loc[filepaths['parameter'] == var_data, 'value'].values[0]
    if not os.path.exists(fn_data):
        raise FileNotFoundError(f"Data file not found: '{fn_data}'.")
    df = pd.read_csv(fn_data, low_memory=False)
    print(f"Number of rows in the data file: {df.shape[0]}")

    # Output file ("flagged_file")
    var_data = "flagged_file"
    if var_data not in filepaths['parameter'].values:
        raise KeyError(f"Output file path not found in the parameters file: '{var_data}'.")
    fn_flagged = filepaths.loc[filepaths['parameter'] == var_data, 'value'].values[0]
    flagged_dir = os.path.dirname(fn_flagged) or "." 
    os.makedirs(flagged_dir, exist_ok=True) # Create necessary directories

    ## Run automated fraud detection
    print(f"Dimensions of dataframe before applying the flags: {df.shape}.")

    # Get initial flags and flag groups
    df = df.pipe(fraud_detection.flag_responses,
                params_sheet='flags')
    # Get initial response classification
    df[['FLAG', 'FLAG_RULE']] = df.pipe(
        fraud_detection.classify_responses, 
        params_sheet='initial_classification_rules'
    )    

    # Add MANUAL_FLAG and MANUAL_COMMENT columns
    if 'MANUAL_FLAG' not in df.columns:
        df['MANUAL_FLAG'] = np.nan
    if 'MANUAL_COMMENT' not in df.columns:
        df['MANUAL_COMMENT'] = np.nan
    
    #! This is risky as it requires the rows in the same order
    # Copy existing manual flags from existing output file
    # # if os.path.exists(fn_flagged):
    #     df[['MANUAL_FLAG','MANUAL_COMMENT']] = pd.read_csv(fn_flagged)[['MANUAL_FLAG','MANUAL_COMMENT']]

    df.to_csv(fn_flagged, index=False)   # Save to file

    print(f"Dimensions of dataframe after applying the flags: {df.shape}.")

    input("\nPress Enter to exit...")