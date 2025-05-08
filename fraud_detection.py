## Libraries
import os
import sys
import re
import time
import json
import numpy as np
import pandas as pd
import functools # Logging
import traceback
# Adds an exit prompt if an error is raised
sys.excepthook = lambda exc_type, exc_value, tb: (
    traceback.print_exception(exc_type, exc_value, tb),
    input("\nPress Enter to exit...")
)

###########################
##### BASIC FUNCTIONS #####
###########################

## Verify parameters file 
FN_PARAMETERS = './config/parameters.xlsx'  # Path to the parameters file
if not os.path.exists(FN_PARAMETERS):
    raise FileNotFoundError(f"Parameters file not found at '{FN_PARAMETERS}'.")

def read_parameters_sheet(sheet_name):
    """
    Reads a specific worksheet from the parameters Excel file.

    Parameters:
        sheet_name (str): The name of the worksheet to read.

    Returns:
        params (pd.DataFrame): DataFrame containing the sheet's contents.
    """
    excel_file = pd.ExcelFile(FN_PARAMETERS)
    if sheet_name not in excel_file.sheet_names:
        raise KeyError(
            f"Worksheet '{sheet_name}' not found in '{FN_PARAMETERS}'. "
            f"Available sheets: {excel_file.sheet_names}"
        )
    return pd.read_excel(excel_file, sheet_name=sheet_name)

## Read file paths provided by the user
filepaths = read_parameters_sheet(sheet_name="filepaths")

###################################
##### FRAUD DETECTION METHODS #####
###################################

def summary_wrapper(func):
    """
    Wrapper function to run a method, log execution time and flag summary,
    and handle exceptions gracefully without interrupting the pipeline.

    Parameters:
        func (function): The function to be wrapped.

    Returns:
        function: A wrapped version of the input function.
    """
    @functools.wraps(func)  # Preserve the name and docstring of the function
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        flag = kwargs.get('flag')
        method_name = flag if flag else func.__name__
        try:
            result = func(*args, **kwargs)
            # Error handling for method
            if result is None:
                raise TypeError(
                    f"The dataframe does not exist after executing '{method_name}'. "
                    f"Make sure the corresponding parameters are correct."
                )
            # Flag summary
            if flag:
                print(f"Number of flagged responses for {flag}: {result[flag].sum()}.")

            duration = time.perf_counter() - start
            print(f"'{method_name}' took {duration:.1f} seconds.")
            return result
        
        except Exception as e:
            print(f"ERROR exeucting '{method_name}'.")
            print(f"{type(e).__name__}: {e}")
            duration = time.perf_counter() - start
            print(f"'{method_name}' took {duration:.1f} seconds.")

    return wrapper

##### WITHIN RESPONSE CHECKS #####

@summary_wrapper
def check_ValueInRange(df, flag_name, column_name, lower_threshold, upper_threshold):
    """
    Adds a flag column to the dataframe if the column value is within the threshold.

    Parameters:
        df (pd.DataFrame) : Dataframe with relevant data.
        flag_name (str) : Flag name.
        column_name (str) : Column name to check for threshold.
        lower_threshold (float) : Values >= lower threshold value are flagged.
        upper_threshold (float) : Values <= upper threshold value are flagged.

    Returns:
        df (pd.DataFrame) : Dataframe with the flag.
    """
    mask = (df[column_name] >= lower_threshold) & (df[column_name] <= upper_threshold)
    df[flag_name] = np.where(mask, True, False)
    return df

@summary_wrapper
def check_CustomCondition(df, flag_name, condition):
    """
    Adds a flag column to the dataframe based on the given boolean condition.

    Parameters:
        df (pd.DataFrame) : Dataframe with relevant columns.
        flag_name (str) : Flag name.
        condition (str) : A Boolean condition written in Pandas evaluate expression format. 
            See https://pandas.pydata.org/docs/reference/api/pandas.eval.html for details.

    Returns:
        df (pd.DataFrame) : Dataframe with flag.
    """
    df[flag_name] = df.eval(condition)
    return df

@summary_wrapper
def check_ReverseCodedResponse(df, flag_name, positive_columns, negative_columns, 
                              min_score, max_score, max_correlation=0):
    """
    Adds a flag column to the dataframe if the mean score of reverse-coded items is negatively correlated to the mean score of their counterparts.
    The method normalizes the items based on min_score and max_score, and removes recoding artifacts (e.g., -99 for unanswered items). 
    This method can be applied to constructs that should be negatively correlated as well. 

    Parameters:
        df (pd.DataFrame) : DataFrame with relevant columns.
        flag_name (str) : Flag name.
        positive_columns (List[str]) : List of column names representing positive responses.
        negative_columns (List[str]) : List of column names representing negative responses.
        min_score (int) : Minimum possible score for the columns.
        max_score (int) : Maximum possible score for the columns.
        max_correlation (float) : Correlation above which the data is flagged.

    Returns:
        df (pd.DataFrame) :Dataframe with the flag.
    """
    # Keeping valid responses within range and normalize score between -1 and 1
    normalize_score = lambda x: (2 * (x - min_score) / (max_score - min_score)) - 1
    data = (df[positive_columns + negative_columns]
            .applymap(lambda x: normalize_score(x) if min_score <= x <= max_score else np.nan))
    
    # Find correlation between means
    mean_positives = data[positive_columns].mean(axis=1)
    mean_negatives = data[negative_columns].mean(axis=1)
    correlation = mean_positives * mean_negatives
    # Positive correlation is suspicious between reverse coded items
    df[flag_name] = np.where(correlation >= max_correlation, True, False)

    return df

@summary_wrapper
def check_SuspiciousCharacter(df, flag_name, list_of_columns, list_of_chars=["\xa0"]):
    """
    Adds a flag column to the dataframe if there are suspicious characters (e.g., non-breaking character) in text response(s).

    Parameters:
        df (pd.DataFrame) : Dataframe with relevant columns.
        flag_name (str) : Flag name.
        list_of_columns (List[str]) : List of column names with text responses.
        list_of_chars (List[str]) : List of suspicious characters to look for. Defaults to ["\xa0"].
            "\xa0": ASCII for the non-breaking character.

    Returns:
        df (pd.DataFrame) : Dataframe with flag.
    """
    # Convert missing data to empty string for character search
    list_of_columns = [col for col in list_of_columns if col in df.columns]
    print(f"Columns being checked for Suspicious Characters: {list_of_columns}")
    text_df = df[list_of_columns].copy()
    text_df = text_df.replace(np.nan, '')
    
    # Check for all characters across all columns
    mask = text_df.map(lambda x: any(char in x for char in list_of_chars)).any(axis=1) 
    df[flag_name] = mask
    return df

@summary_wrapper
def check_SuspiciousName(df, flag_name, column_first_name, column_last_name, min_word_length=2):
    """
    Adds a flag column to the dataframe for suspicious response to first name and last name columns.
    This flag only works if the first name and last name are collectde in two separate text responses. 
    A response is considered suspicious if any one of the name fields repeats a word (while ignoring initials) from the other name field.

    Parameters:
        df (pd.DataFrame) : Dataframe with relevant columns.
        flag_name (str) : Flag name. 
        column_first_name (str) : Column name for the first name.
        column_last_name (str) : Column name for the last name.
        min_word_length (int) : Minimum length of a word to be considered for matching.
            Defaults to the recommended value of 2 to avoid initials. 

    Returns:
        df (pd.DataFrame) : Dataframe with flag.
    """
    def compare_names(row, min_word_length=min_word_length):
        """
        Search for common (min_word_length) letter words in first and last name ignoring the lettercase.
        """
        pattern = fr"(\w{{{min_word_length},}})"
        
        first_name_set = []
        last_name_set = []
        # Strip and lowercase names for matching
        if not pd.isna(row[column_first_name]):
            first_name =  row[column_first_name].lower().strip()
            first_name_set = (re.findall(pattern, first_name))
        
        if not pd.isna(row[column_last_name]):
            last_name = row[column_last_name].lower().strip()
            last_name_set = (re.findall(pattern, last_name))

        common_items = set(first_name_set) & set(last_name_set)
        
        return True if (len(common_items) > 0) else False 
    
    # Check for all characters in all columns
    df[flag_name] = df.apply(compare_names, axis=1)
    return df

@summary_wrapper
def check_IPLocation(df, flag_name, column_ip, target_region, flag_missing, region_level='country'):
    """
    Adds a region location column `IPLocation` and a flag column to the dataframe based on the IP address.

    Parameters:
        df (pd.DataFrame) : Dataframe with relevant columns.
        flag_name (str) : Flag name.
        column_ip (str) : Column name for IP address. 
        target_region (str) : Region name that should not be flagged. See the notes below for details. Defaults to 'country'.
        flag_missing (bool) : Should missing data be flagged? True means missing data is flagged.
        region_level (str) : The geographic level of the region to check. Can be either 'country', 'state', or 'city'. 
            For example, 'country' as "US", 'state' as "California", and 'city' as "Mountain View".

    Returns:
        df (pd.DataFrame) : Dataframe with flag.
    """
    import geocoder
    if region_level == 'country':
        df['IPLocation'] = df[column_ip].apply(lambda x: geocoder.ip(x).country)
    elif region_level == 'state':
        df['IPLocation'] = df[column_ip].apply(lambda x: geocoder.ip(x).state)
    elif region_level == 'city':
        df['IPLocation'] = df[column_ip].apply(lambda x: geocoder.ip(x).city)
    else:
        raise ValueError("The region_level should be either \'country\', \'state\', or \'city\'.")

    if flag_missing:
        mask = np.where(
            (df['IPLocation'] == target_region), 
            False, True
        )
    else:
        mask = np.where(
            ((df['IPLocation'] == target_region) | (df['IPLocation'].isna())), 
            False, True
        )
    df[flag_name] = mask

    return df

@summary_wrapper
def check_LatLongLocation(df, flag_name, column_latitude, column_longitude, target_country, flag_missing):
    """
    Adds a country column `LatLongLocation` and a flag column to the dataframe based on Latitude-Longtitude.

    Parameters:
        df (pd.DataFrame) : Dataframe with relevant columns.
        flag_name (str) : Flag name.
        column_latitude (str) : Column name for Latitude.
        column_longitude (str) : Column name for Longitude.
        target_country (str) : Country name that should not be flagged. Verifies against the country's full name (e.g., "United States of America").
        flag_missing (bool) : Should missing data be flagged? True means missing data is flagged.

    Returns:
        df (pd.DataFrame) : Dataframe with flag.
    """    
    import geopandas as gpd # LatLong
    from shapely.geometry import Point # LatLong

    def read_world_shape(fn):
        """
        Returns a Shapely dataframe with geometries of all countries

        Parameters:
            fn (str) : Location of shape file.

        Returns:
            df (pd.DataFrame) : Dataframe with country 'name', 'iso3', and 'geometry'.
        """
        # Reading the shapefile
        df = gpd.read_file(fn) 
        df = df[['name', 'iso3', 'geometry']] 
    
        # Search priority for countries that appear in the data often (these can be modified to improve performance)
        df['priority'] = np.nan # Creating additional column for counting country incidence
        df.loc[df.name=="United States of America", 'priority'] = 0
        df.loc[df.name=="China", 'priority'] = 1
        df.loc[df.name=="India", 'priority'] = 2

        df = df.sort_values(by='priority')

        return df
    
    # Read world shapefile data
    var_data = "world_shape_file"
    if var_data not in filepaths['parameter'].values:
        raise KeyError(
            f"'world_shape_file' path not found in the parameters file. "
            f"This shapefile is required to get country's name from latitude-longitude."
        )
    fn = filepaths.loc[filepaths['parameter'] == var_data, 'value'].values[0]
    df_world = read_world_shape(fn) # Need this for get_latlong_country()

    def get_latlong_country(lat, long):
        """
        Returns the country and state of the given lat-long. Requires `df_world` dataframe.

        Parameters:
            lat (float) : Latitude in degrees.
            long (float) : Longitude in degrees.

        Returns:
            country (str) : Country name. 
        """
        if np.isnan(long) or np.isnan(lat):
            return np.nan
        point = Point(long, lat) # Note that it is long-lat in Point()

        # Use the spatial index to speed up the querying
        possible_matches_index = df_world.sindex.query(point, predicate="intersects")
        possible_matches = df_world.iloc[possible_matches_index]
        
        # Searching for the point in country's geometry
        for _, row in possible_matches.iterrows():
            if point.within(row['geometry']):
                return row['name'] # Country

        return np.nan
    
    df['LatLongLocation'] = df.apply(
        lambda x: get_latlong_country(x[column_latitude], x[column_longitude]), axis=1
    )
    
    if flag_missing:
        mask = np.where(
            (df['LatLongLocation'] == target_country), 
            False, True
        )
    else:
        mask = np.where(
            ((df['LatLongLocation'] == target_country) | (df['LatLongLocation'].isna())), 
            False, True
        )
    df[flag_name] = mask
        
    return df

##### BETWEEN RESPONSE CHECKS #####

@summary_wrapper
def check_MultipleIPAttempts(df, flag_name, column_ip, column_success, num_attempts_lower, 
                            num_attempts_upper=np.inf, attempt_type='successful', column_terminate=None):
    """
    Adds a flag column to the dataframe for multiple attempts from the same IP network (i.e., the first three octets; e.g., 8.8.8).
    Also adds a `IPNetwork` columns to the dataframe. 
    The function can be defined to provide a lower bound and an upper bound to count the attempts. 
    It can also be modified to consider a specific type of attempt (e.g., successful or incomplete). 

    Parameters:
        df (pd.DataFrame) : Dataframe with relevant columns.
        flag_name (str) : Flag name.
        column_ip (str) : Column name with IP address.
        column_success (str) : Column name with a non-empty response treated as a successful attempt.
            "column_success" should typically be a question towards the end of the survey.
        num_attempts_lower (int) : Minimum number of attempts from the same IP to be flagged (>=).
        num_attempts_upper (int) : Maximum number of attempts from the same IP to be flagged (<=).
            Defaults to np.inf.
        attempt_type (str) : Type of attempt to flag. Defaults to 'successful'.
            - 'successful' : attempts have a response for the `column_success` question.
            - 'unsuccessful' : attempts do not have a response for the `column_success` question.
            - 'incomplete' : attempts have no response for the `column_success` question and has no terminate flag. A subset of 'unsuccessful' attempts.
            - 'failed' : attempts have no response for the `column_success` question and has a terminate flag. A subset of 'unsuccessful' attempts.
            - 'all' : attempts irrespective of if it is successful or not.
        column_terminate (str) : Column name with terminate flag. Optional for 'successful' attempt.

    Returns:
        df (pd.DataFrame) : Dataframe with flag.

    Notes:
        Qualtrics can recode "Seen but unanswered questions" as -99. These are treated as "successful".
        Qualtrics `Q_TerminateFlag` column marks unsuccessful responses as "Screened" or "QuotaMet".
        A terminate flag (like `Q_TerminateFlag`) is required for 'incomplete' and 'failed' attempts. 
    """
    
    def count_attempts(group):
        """
        Adds flags if number of attempts exceed the maximum attempt type
            
        Parameters:
            group (pd.groupby): Group with the same IP network.
            
        Returns:
            group (pd.groupby): Group with the attempt type flag.
        """
        if attempt_type == 'successful':
            group[f'num_attempts_{attempt_type}'] = group[column_success].notna().sum()
        elif attempt_type == 'unsuccessful':
            group[f'num_attempts_{attempt_type}'] = group[column_success].isna().sum()
        elif attempt_type == 'incomplete':
            group[f'num_attempts_{attempt_type}'] = (group[column_success].isna() & group[column_terminate].isna()).sum()
        elif attempt_type == 'failed':
            group[f'num_attempts_{attempt_type}'] = (group[column_success].isna() & group[column_terminate].notna()).sum()
        elif attempt_type == 'all':
            group[f'num_attempts_{attempt_type}'] = group.index.size
        else:
            raise ValueError(f"Invalid attempt_type: {attempt_type}.")
            
        group[flag_name] = np.where(
            ((group[f'num_attempts_{attempt_type}'] >= num_attempts_lower) 
            & (group[f'num_attempts_{attempt_type}'] <= num_attempts_upper)),
            True, False
        )
        
        return group
    
    # Add a column for the network portion of the IP address (ignoring the host/device portion)
    df['IPNetwork'] = df[column_ip].apply(lambda ip: '.'.join(ip.split('.')[:3]))
    df = df.groupby('IPNetwork', group_keys=False).apply(count_attempts, include_groups=False)
    
    return df

@summary_wrapper
def check_BurstResponses(df, flag_name, column_start_time, column_duration,
                        max_start_time_difference, max_duration_difference, 
                        unflag_start_time_difference=None, unflag_duration_difference=None):
    """
    Adds a flag column to the dataframe for burst of responses with similar start times and durations.
    Adds an additional column with number of burst responses `NumBurstResponses`.
    This method implements a lower bound and an upper bound for start time and duration differences to allow for graded flagging. 

    Parameters:
        df (pd.DataFrame) : Dataframe with relevant columns.
        flag_name (str) : Flag name.
        column_start_time (str) : Column name for survey start date and time.
        column_duration (str) : Column name for survey duration.
        max_start_time_difference (int) : Maximum absolute difference between start times.
        max_duration_difference (int) : Maximum absolute difference between survey durations.
        unflag_start_time_difference (int) : Maximum start time difference for not flagging the responses.
        unflag_duration_difference (int) : Maximum duration difference for not flagging the responses.
        
    Returns:
        df (pd.DataFrame) : Dataframe with flag.
    """
    # Copying dataframe and converting start time column to datetime 
    nearby_df = df[[column_start_time, column_duration]].copy()
    nearby_df[column_start_time] = pd.to_datetime(nearby_df[column_start_time])
    
    def get_num_responses(row, max_start, max_duration):
        """
        Returns indices of all rows that are within the maximum start time and duration threshold for the input row.
            
        Parameters:
            row (pd.Series): A single row of the dataframe. 
            max_start_time (int) : Maximum absolute difference between start times.
            max_duration (int) : Maximum absolute difference between survey durations.
            
        Returns:
            num_responses (int) : Number of nearby responses near the input row.
        """
        # Start time and duration must exist (may have missing data if multiple surveys are merged)
        if pd.isna(row[column_start_time]) or pd.isna(row[column_duration]):
            return np.nan
        
        diff_start_time = np.abs((nearby_df[column_start_time] - row[column_start_time]).dt.total_seconds())
        diff_duration = np.abs(nearby_df[column_duration] - row[column_duration])
        
        mask = ((diff_start_time <= max_start) 
                & (diff_duration <= max_duration))
        
        idxs = mask[mask].index # Get indexes of nearby responses
        # idxs can be empty if min_start_time_difference != 0
        if row.name in idxs:
            idxs = idxs.drop(row.name) # Remove self index
            
        num_responses = idxs.size
        return num_responses
    
    # Unflagging when using multiple burst flags (to avoid double counting)
    nearby_df['unflag'] = 0
    if unflag_start_time_difference and unflag_duration_difference:
        nearby_df['unflag'] = nearby_df.apply(get_num_responses, 
                                       max_start=unflag_start_time_difference, 
                                       max_duration=unflag_duration_difference,
                                       axis=1) 
    
    # Add a column with number of similar responses
    num_col = f"F{flag_name}_count"
    df[num_col] = (nearby_df.apply(get_num_responses, 
                                  max_start=max_start_time_difference, 
                                  max_duration=max_duration_difference,
                                  axis=1)
                  - nearby_df['unflag'])
    
    df[flag_name] = np.where(df[num_col] > 0, True, False)
    return df

@summary_wrapper
def check_DuplicatedText(df, flag_name, list_of_columns, min_length, max_length, 
                                 search_strategy='column', create_column_flag=False):
    """
    Adds a flag column to the dataframe for duplicated text response of specified length.
        
    Parameters:
        df (pd.DataFrame) : Dataframe with relevant columns.
        flag_name (str) : Flag name.
        list_of_columns (List[str]) : List of column names for text responses.
        min_length (int) : Minimum string length of text responses.
        max_length (int) : Maximum string length of text responses.
        search_strategy (str) : Search strategy to mark duplicates. Defaults to 'column'.
            - 'column' looks for duplicates within each text column and flags if any of the columns contains a duplicate. 
                This strategy creates flags for individual columns as well.
            - 'all' looks for duplicates across all text columns.
        create_column_flag (boolean): Bollean to add column-wise flag. Defaults to False.
        
    Returns:
        df (pd.DataFrame) : Dataframe with flag.
    """
    # Create individual flag for columns with duplicates
    df[flag_name] = False
    
    # Convert string object (if any) to list
    if isinstance(list_of_columns, str):
        list_of_columns = [list_of_columns]
    
    ## Search strategies
    if search_strategy == 'column':
        for col in list_of_columns:
            # Strips and lowercase all text responses
            lower_df = df[col].str.lower().str.strip()
            mask = (
                (lower_df.str.len() >= min_length) 
                & (lower_df.str.len() <= max_length)
                & (lower_df.str.lower().duplicated(False))
                & (~lower_df.isna())
            )
            # Create a flag for each individual column
            if create_column_flag and len(list_of_columns) > 1:
                flag_name_col = f"{flag_name}_{col}"
                df[flag_name_col] = mask 
    
            # Combined flag across all columns. Marks if any column value is duplicated
            df[flag_name] |= mask # Use |= for any column flagged and &= for all column flagged
        
    elif search_strategy == 'all':
        # Flatten the dataFrame while preserving the original index
        flattened_df = pd.DataFrame(df[list_of_columns].stack(dropna=False)).reset_index()
        # 'level_0' is the original index, and 0 are the values
        flattened_df.columns = ['original_index', 'column', 'value']
        # Strips and lowercase all text responses
        flattened_df['value'] = flattened_df['value'].str.lower().str.strip()
        
        # Check for duplicates (count number of occurences within the entire dataframe)
        duplicates_all = flattened_df.groupby(['value'])['original_index'].transform('size')
        duplicates = ((duplicates_all > 1) # number of occurences > 1
                      & (flattened_df['value'].str.len() >= min_length)  # string length check
                      & (flattened_df['value'].str.len() <= max_length))
        # Map these duplicate flag_names back to the original DataFrame's index
        df[flag_name] = df.index.isin(flattened_df['original_index'][duplicates])

    else:
        raise ValueError(f"The search strategy should be either 'column' or 'all'. Instead, the strategy provided is \'{search_strategy}\'.")
        
    return df


###################################
##### RESPONSE CLASSIFICATION #####
###################################

def decode_special_floats(dct):
    """
    Converts the special values (e.g., infinity) in the JSON object in the parameters file to Python numeric values. 
    The parameters file accepts the following values:
        Positive infinity as "infinity" or "inf".
        Negative infinity as "-infinity" or "-inf".
        Empty or missing values as "nan", "nil", or "none".
        True as "true".
        False as "false".

    Parameters:
        dct (dict) : Dictionary with JSON values.
        
    Returns:
        dct (dict) : Dictionary with corresponding Python values.
    """
    for key, value in dct.items():
        value = value.lower() if isinstance(value, str) else value
        if value == "infinity" or value == "inf":
            dct[key] = np.inf
        elif value == "-infinity" or value == "-inf":
            dct[key] = -np.inf
        elif value == "nan" or value == "nil" or value == "none":
            dct[key] = np.nan
        elif value == "true":
            dct[key] = True
        elif value == "false":
            dct[key] = False
    return dct

def flag_responses(df, params_sheet, add_string=True):
    """
    Applies the flags provided by the user. 

    Parameters:
        df (pd.DataFrame) : Dataframe with survey data. 
        params_sheet (str) : Excel sheet name in the parameters file with flag information ('flags')
            Must contain columns 'flag_name', 'method_name', 'flag_group', 'use_flag', 'parameters'.
        add_string (boolean) : Whether to add string-formatted columns for activated flags and flag groups. Defaults to True.

    Returns:
        df (pd.DataFrame) : Dataframe with added flag and flag group columns.
    """
    ## Reading flag parameters
    params = read_parameters_sheet(sheet_name=params_sheet)
    # Verify necessary columns
    required_columns = ['flag_name', 'method_name', 'flag_group', 'use_flag', 'parameters']
    missing = [col for col in required_columns if col not in params.columns]
    if missing:
        raise ValueError(f"Missing required columns in sheet '{params_sheet}': {missing}")
    # Drop inactive flags
    params = params[params['use_flag'] == 1] 

    ## Apply individual flags
    for _, row in params.iterrows():
        print(f"\n***** Executing: {row['flag_name']} *****")
        # Read `parameters` columns in JSON format while decoding special floats
        flag_parameters = json.loads(row['parameters'], object_hook=decode_special_floats)

        df = df.pipe(
            eval(row['method_name']),       # Method to implement `method_name`
            flag_name=row['flag_name'],     # Flag name `flag_name`
            **flag_parameters               # Flag parameters `parameters`
        )
      
    ## Add flag count by flag group
    dict_flags = params.groupby('flag_group')['flag_name'].agg(list)    # List of flags for each flag group
    for flag_group, list_flags in dict_flags.items():
        df[flag_group] = df[list_flags].sum(axis=1)                     # Each flag in list_flags is a Boolean column 

    ## Add string-formatted columns for activated flags and flag groups
    if add_string:
        df['ActiveFlags'] = (
            df[params['flag_name'].dropna().values]                             # Selecting relevant columns 
            .astype(bool)                                                       # Converts 0 to False
            .apply(lambda row: '; '.join(row[row].index.to_list()), axis=1)     # Join the column labels with True
        )
        df['ActiveFlagGroups'] = (
            df[params['flag_group'].dropna().unique()]                          # Selecting relevant columns 
            .astype(bool)                                                       # Converts 0 to False
            .apply(lambda row: '; '.join(row[row].index.to_list()), axis=1)     # Join the column labels with True
        )

    return df

def classify_responses(df, params_sheet):
    """
    Applies fraud classification rules loaded from an Excel file. Rules must be listed in the descending order of importance.

    Parameters:
        df (pd.DataFrame) : Dataframe with flag groups and relevant indicators.
        params_sheet (str) : Excel sheet name in parametrs file with rule logic ('initial_classification_rules').
            Must contain columns 'rule_num', 'condition_expr', 'classification', 'use_rule'.

    Returns:
        classified_rules (pd.DataFrame) : Dataframe with flag `classification` and `rule_num` columns.
    """
    ## Reading classification rule parameters
    params = read_parameters_sheet(sheet_name=params_sheet)
    # Verify necessary columns
    required_columns = ['rule_num', 'condition_expr', 'classification', 'use_rule']
    missing = [col for col in required_columns if col not in params.columns]
    if missing:
        raise ValueError(f"Missing required columns in sheet '{params_sheet}': {missing}")
    # Drop inactive flags
    params = params[params['use_rule'] == 1] 

    def evaluate_rules(row):
        """
        Sequentially applies classification rules from the parameters to each response.
        Stops exceuting further rules if a rules requirements are met. 
        Raises an error if any rule cannot be evaluated.

        Parameters:
            row (pd.Series) : A single row of the dataframe with required columns. 

        Returns:
            Tuple : A tuple with 'classification' and 'rule_num'.  
        """
        local_dict = row.to_dict()
        for _, rule in params.iterrows():
            try:
                if eval(rule['condition_expr'], {}, local_dict):
                    return (rule['classification'], rule['rule_num'])
            except Exception as e:
                raise ValueError(f"Error in {rule['rule_num']} using the expression: {rule['condition_expr']}.")
            
        return ('VALID', None) 

    classified_rules = df.apply(evaluate_rules, axis=1, result_type='expand') # Dataframe with two columns

    return classified_rules  

#################################
##### DESCRIPTIVE AND PLOTS #####
#################################

def print_flag_counts(df, params_sheet):
    """
    Prints out simple counts of flags and flag groups. 

    Parameters:
        df (pd.DataFrame) : Dataframe with survey data. 
        params_sheet (str) : Excel sheet name with flag information ('flags').
            Must contain columns 'flag_name', 'method_name', 'flag_group', 'use_flag', 'parameters'.

    Returns:
        None : This function prints response classification counts. 
    """
    ## Reading flag parameters
    params = read_parameters_sheet(sheet_name=params_sheet)
    # Verify necessary columns
    required_columns = ['flag_name', 'method_name', 'flag_group', 'use_flag', 'parameters']
    missing = [col for col in required_columns if col not in params.columns]
    if missing:
        raise ValueError(f"Missing required columns in sheet '{params_sheet}': {missing}")
    # Drop inactive flags
    params = params[params['use_flag'] == 1] 

    flags = params['flag_name'].unique()
    print(f"Number of unique responses flagged: {df[flags].any(axis=1).sum()} out of {df.shape[0]}") # Total rows with at least one flag
    print(f"\nFlags:\n{df[flags].sum().to_frame(name='Count')}") # Table of flag counts

    flag_groups = params['flag_group'].dropna().unique()
    print(f"\nFlag Groups:\n{df[flag_groups].sum().to_frame(name='Count')}") # Table of flag group counts

    return None

def print_classification_counts(df, flag_column):
    """
    Prints out simple counts of flags and flag groups. 

    Parameters:
        df (pd.DataFrame) : Dataframe with survey data. 
        flag_column (str) : Column name for the flag classification. 
            'FLAG' for algorithmic flags, 'MANUAL_FLAG' for manual check flags, 'FINAL_FLAG' for combined flags. 

    Returns:
        None : This function prints flag counts and flag group counts. 
    """

    print(f"Response classification: {flag_column}\n{df[flag_column].value_counts().rename_axis(None).to_frame(name='Count')}")

    return None

def plot_flag_cooccurrence_heatmap(df, flag_columns,
                                  params_sheet,
                                  use_groups=False,
                                  save_folder=None,
                                  display_figure=False):
    """
    Plots a square heatmap of co-occurrence between flags (or flag groups) and the response classification.

    Parameters:
        df (pd.DataFrame) : Dataframe with survey data and flags.
        flag_columns (List[str]) : Column names containing the classification (e.g., 'FLAG', 'MANUAL_FLAG', or 'FINAL_FLAG').
        params_sheet (str) : Excel sheet name with flag information ('flags').
            Must contain columns 'flag_name', 'method_name', 'flag_group', 'use_flag', 'parameters'.
        use_groups (bool) : If True, use flag groups instead of individual flags.
        save_folder (str) : Optional folder path to save the heatmap.
        display_figure (bool) : If True, display created figures. Defaults to True.

    Returns:
        None : Displays a seaborn heatmap.
    """
    import seaborn as sns
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    ## Reading classification rule parameters
    params = read_parameters_sheet(sheet_name=params_sheet)
    # Verify necessary columns
    required_columns = ['flag_name', 'method_name', 'flag_group', 'use_flag', 'parameters']
    missing = [col for col in required_columns if col not in params.columns]
    if missing:
        raise ValueError(f"Missing required columns in sheet '{params_sheet}': {missing}")
    # Drop inactive flags
    params = params[params['use_flag'] == 1] 

    # Identify relevant flag columns
    column_key = 'flag_group' if use_groups else 'flag_name'
    columns = [col for col in params[column_key].dropna().unique() if col in df.columns]
    
    missing_cols = [col for col in flag_columns if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing column(s) in DataFrame: {', '.join(missing_cols)}")

    # Binary matrix for classifications
    classification_dummies = pd.get_dummies(df[flag_columns], prefix="", prefix_sep="")
    classification_df = (
        classification_dummies
        .astype(bool)
        .fillna(False)
        .astype(int)
    )
    flag_df = (
        df[columns]
        .astype(bool)
        .fillna(False)
        .astype(int)
    )
    # Combine and compute co-occurrence matrix
    combined = pd.concat([flag_df, classification_df], axis=1)
    co_matrix = combined.T @ combined  # True count of co-occurrences (dot product)

    # Initialize heatmap
    fontsize = 16
    _, ax = plt.subplots(figsize=(1.0 * len(co_matrix), 1.0 * len(co_matrix)))
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size=0.3, pad=0.1)

    heatmap = sns.heatmap(co_matrix, annot=True, fmt='d', cmap='YlGnBu',
                          annot_kws={"size": fontsize}, cbar_ax=cax, ax=ax,
                          linewidths=0.3, linecolor='white')

    ax.set_title(f"Co-occurrence of {'Flag Groups' if use_groups else 'Flags'} and classified responses ({'-'.join(flag_columns)})", fontsize=fontsize)
    ax.set_xticklabels(ax.get_xticklabels(), fontsize=fontsize, rotation=90)
    ax.set_yticklabels(ax.get_yticklabels(), fontsize=fontsize, rotation=0)
    ax.set_aspect('equal', adjustable='box') # Square heatmap

    # Force colorbar ticks to be integers
    cbar = heatmap.collections[0].colorbar
    cbar.ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    cbar.ax.tick_params(labelsize=fontsize)

    # Prepare group boundaries for visual separation
    if use_groups:
        df_flags = params[['flag_group']].dropna().drop_duplicates().reset_index(drop=True)
    else:
        df_flags = params[['flag_name', 'flag_group']].fillna('EMPTY')
        df_flags = df_flags[df_flags['flag_name'].isin(columns)].reset_index(drop=True)

    group_boundaries = []
    for group in df_flags['flag_group'].unique():
        max_index = df_flags[df_flags['flag_group'] == group].index.max()
        group_boundaries.append(max_index)
    group_boundaries = sorted(set(group_boundaries))

    # Draw visual borders
    flag_end_index = len(columns) - 1
    total_size = len(co_matrix)
    # Starting border (left and top)
    ax.axhline(0, color='black', linewidth=2)
    ax.axvline(0, color='black', linewidth=2)

    if not use_groups:
        for boundary in group_boundaries:
            ax.axhline(boundary + 1, color='black', linewidth=2)
            ax.axvline(boundary + 1, color='black', linewidth=2)

    # Classfication border
    ax.axhline(flag_end_index + 1, color='black', linewidth=3)
    ax.axvline(flag_end_index + 1, color='black', linewidth=3)
    # Ending border (right and bottom)
    ax.axhline(total_size, color='black', linewidth=3)
    ax.axvline(total_size, color='black', linewidth=3)

    # Save and Display
    plt.tight_layout()
    if save_folder:
        if not os.path.exists(save_folder):
            raise FileNotFoundError(f"The folder path {save_folder} does not exist.")
        fn = os.path.join(save_folder, f"{'FG' if use_groups else 'F'}-{'-'.join(flag_columns)}_{time.strftime('%y%m%d-%H%M%S')}.jpg")
        plt.savefig(fn, dpi=300, bbox_inches='tight')
    if display_figure:
        plt.show()

if __name__ == "__main__":
    pass

