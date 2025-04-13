# Implement fuzzy-string
from fraud_detection import filepaths

if __name__ == "__main__":
    ## Verify and read data
    # Manually checked file ("manual_file")
    var_data = "manual_file"
    if var_data not in filepaths['parameter'].values:
        raise KeyError(f"Manually checked file path not found in the parameters file: '{var_data}'.")
    fn_manual = filepaths.loc[filepaths['parameter'] == var_data, 'value'].values[0]

    print(f"This step requires the user to manually classify each response by adding "
          f"a classification flag in the MANUAL_FLAG column in the `{fn_manual}` file. "
          f"Proceed to the next step after manual classification is compelete.")

    input("\nPress Enter to exit...")