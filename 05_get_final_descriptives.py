import os
import numpy as np
import pandas as pd
import fraud_detection
from fraud_detection import filepaths

if __name__ == "__main__":
    ## Verify and read data
    # Final output file ("final_output_file")
    var_data = "final_output_file"
    if var_data not in filepaths['parameter'].values:
        raise KeyError(f"Final output file path not found in the parameters file: '{var_data}'.")
    fn_output = filepaths.loc[filepaths['parameter'] == var_data, 'value'].values[0]
    if not os.path.exists(fn_output):
        raise FileNotFoundError(f"Final output data file not found: '{fn_output}'.")
    df = pd.read_csv(fn_output, low_memory=False)

    ## Get descriptives
    fraud_detection.print_classification_counts(df, flag_column='FLAG')
    fraud_detection.print_classification_counts(df, flag_column='MANUAL_FLAG')
    fraud_detection.print_classification_counts(df, flag_column='FINAL_FLAG')

    ## Plot results
    var_data = "figure_folder"
    if var_data in filepaths['parameter'].values:
        figure_folder = filepaths.loc[filepaths['parameter'] == var_data, 'value'].values[0]
        # Create necessary directories
        os.makedirs(figure_folder, exist_ok=True)
        fraud_detection.plot_flag_cooccurrence_heatmap(df, flag_columns=['FLAG','MANUAL_FLAG','FINAL_FLAG'], 
                                                      params_sheet='flags', use_groups=False, save_folder=figure_folder)
        fraud_detection.plot_flag_cooccurrence_heatmap(df, flag_columns=['FLAG','MANUAL_FLAG','FINAL_FLAG'], 
                                                      params_sheet='flags', use_groups=True, save_folder=figure_folder)

    else:
        print("Plots are not saved as 'figure_folder' is not provided in the parameters file.")
        fraud_detection.plot_flag_cooccurrence_heatmap(df, flag_columns=['FLAG','MANUAL_FLAG','FINAL_FLAG'], 
                                                      params_sheet='flags', use_groups=False, display_figure=False)
        fraud_detection.plot_flag_cooccurrence_heatmap(df, flag_columns=['FLAG','MANUAL_FLAG','FINAL_FLAG'], 
                                                      params_sheet='flags', use_groups=True, display_figure=False)

    input("\nPress Enter to exit...")