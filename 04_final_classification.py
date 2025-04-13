import os
import numpy as np
import pandas as pd
import fraud_detection
from fraud_detection import filepaths

if __name__ == "__main__":
    ## Verify and read data
    # Manually checked file ("manual_file")
    var_data = "manual_file"
    if var_data not in filepaths['parameter'].values:
        raise KeyError(f"Manually checked file path not found in the parameters file: '{var_data}'.")
    fn_manual = filepaths.loc[filepaths['parameter'] == var_data, 'value'].values[0]
    if not os.path.exists(fn_manual):
        raise FileNotFoundError(f"Output data file not found: '{fn_manual}'.")
    df = pd.read_csv(fn_manual, low_memory=False)

    # Final output ("final_output_file")
    var_data = "final_output_file"
    if var_data not in filepaths['parameter'].values:
        raise KeyError(f"Final output file path not found in the parameters file: '{var_data}'.")
    fn_output = filepaths.loc[filepaths['parameter'] == var_data, 'value'].values[0]
    output_dir = os.path.dirname(fn_output) or "." 
    os.makedirs(output_dir, exist_ok=True) # Create necessary directories

    # Verify FLAG and MANUAL_FLAG columns
    if 'FLAG' not in df.columns:
        raise ValueError("The automated classification column 'FLAG' not found in the data file.")
    if 'MANUAL_FLAG' not in df.columns:
        raise ValueError("The manual classification column 'MANUAL_FLAG' not found in the data file.")
    if df['MANUAL_FLAG'].empty:
        print("WARNING: The file does not have any manual flags.")

    print(f"Dimensions of dataframe before combining automated and manual flags: {df.shape}.")
    df[['FINAL_FLAG', 'FINAL_FLAG_RULE']] = df.pipe(
        fraud_detection.classify_responses, 
        params_sheet='final_classification_rules'
    )

    df.to_csv(fn_output, index=False)   # Save to file
    print(f"Dimensions of dataframe after combining automated and manual flags: {df.shape}.")

    input("\nPress Enter to exit...")