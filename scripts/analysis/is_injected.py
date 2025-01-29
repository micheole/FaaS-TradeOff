import pandas as pd
import math
import sys
import argparse

def load_data(csv_file):
    """
    Loads the benchmarking data from a CSV file.

    Args:
        csv_file (str): Path to the CSV file.

    Returns:
        pd.DataFrame: Loaded DataFrame.
    """
    try:
        df = pd.read_csv(csv_file)
        return df
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)

def preprocess_data(df):
    """
    Preprocesses the data by ensuring correct data types and handling missing values.

    Args:
        df (pd.DataFrame): The raw benchmarking DataFrame.

    Returns:
        pd.DataFrame: Preprocessed DataFrame.
    """
    # Ensure correct data types
    df['Mean_Duration_ms'] = pd.to_numeric(df['Mean_Duration_ms'], errors='coerce')
    df['CI_Lower_ms'] = pd.to_numeric(df['CI_Lower_ms'], errors='coerce')
    df['CI_Upper_ms'] = pd.to_numeric(df['CI_Upper_ms'], errors='coerce')
    df['Trial_Count'] = pd.to_numeric(df['Trial_Count'], errors='coerce')
    df['Num_Runs'] = pd.to_numeric(df['Num_Runs'], errors='coerce')

    # Drop rows with missing essential data
    df = df.dropna(subset=['Function', 'Trial_Count', 'Mean_Duration_ms', 'CI_Lower_ms', 'CI_Upper_ms', 'Num_Runs'])

    return df

def group_similar_runs(df, tolerance_runs=5):
    """
    Groups logs with similar Num_Runs within a specified tolerance.

    Args:
        df (pd.DataFrame): The benchmarking DataFrame.
        tolerance_runs (int): Allowed difference in Num_Runs to consider as similar.

    Returns:
        pd.DataFrame: DataFrame with an additional 'Run_Group' column.
    """
    df = df.sort_values(['Function', 'Num_Runs', 'Trial_Count']).reset_index(drop=True)
    df['Run_Group'] = 0  # Initialize group identifier

    for func in df['Function'].unique():
        func_df = df[df['Function'] == func].sort_values('Num_Runs').reset_index(drop=True)
        group_id = 1
        func_df.at[0, 'Run_Group'] = group_id

        for i in range(1, len(func_df)):
            current_runs = func_df.at[i, 'Num_Runs']
            previous_runs = func_df.at[i-1, 'Num_Runs']
            if abs(current_runs - previous_runs) <= tolerance_runs:
                func_df.at[i, 'Run_Group'] = group_id
            else:
                group_id += 1
                func_df.at[i, 'Run_Group'] = group_id

        # Update the main DataFrame
        df.loc[func_df.index, 'Run_Group'] = func_df['Run_Group']

    return df

def calculate_standard_deviation(row, Z):
    """
    Calculates the standard deviation based on confidence intervals.

    Args:
        row (pd.Series): A row from the DataFrame.
        Z (float): Z-score for the desired confidence level.

    Returns:
        float: Calculated standard deviation.
    """
    try:
        sigma = (row['CI_Upper_ms'] - row['CI_Lower_ms']) / (2 * Z / math.sqrt(row['Num_Runs']))
        return sigma
    except:
        return math.nan

def calculate_margin_of_error(row, Z):
    """
    Calculates the Margin of Error (MOE).

    Args:
        row (pd.Series): A row from the DataFrame.
        Z (float): Z-score for the desired confidence level.

    Returns:
        float: Calculated MOE.
    """
    try:
        moe = Z * (row['Standard_Deviation_ms'] / math.sqrt(row['Num_Runs']))
        return moe
    except:
        return math.nan

def assess_accuracy(df, confidence_level=0.95, desired_moe=5):
    """
    Assesses the accuracy of the benchmarking results.

    Args:
        df (pd.DataFrame): The preprocessed and grouped DataFrame.
        confidence_level (float): Desired confidence level for MOE.
        desired_moe (float): Desired margin of error percentage.

    Returns:
        pd.DataFrame: DataFrame with accuracy assessment.
    """
    # Calculate Z-score
    Z = stats.norm.ppf(1 - (1 - confidence_level) / 2)

    # Calculate Standard Deviation
    df['Standard_Deviation_ms'] = df.apply(lambda row: calculate_standard_deviation(row, Z), axis=1)

    # Calculate Margin of Error
    df['Margin_of_Error_ms'] = df.apply(lambda row: calculate_margin_of_error(row, Z), axis=1)

    # Calculate Percentage Margin of Error relative to Mean_Duration_ms
    df['MOE_Percentage'] = (df['Margin_of_Error_ms'] / df['Mean_Duration_ms']) * 100

    # Determine if MOE meets the desired threshold
    df['Meets_Desired_MOE'] = df['MOE_Percentage'] <= desired_moe

    return df

def analyze_proportionality(df, tolerance=5):
    """
    Analyzes whether increasing the input parameter proportionally increases the duration.

    Args:
        df (pd.DataFrame): The DataFrame with accuracy assessment.
        tolerance (float): Acceptable percentage difference between expected and actual duration change.

    Returns:
        list: List of discrepancies.
    """
    discrepancies = []

    for func in df['Function'].unique():
        func_df = df[df['Function'] == func]
        run_groups = func_df['Run_Group'].unique()

        for group in run_groups:
            group_df = func_df[func_df['Run_Group'] == group].sort_values('Trial_Count').reset_index(drop=True)

            for i in range(1, len(group_df)):
                prev_trial = group_df.at[i-1, 'Trial_Count']
                curr_trial = group_df.at[i, 'Trial_Count']
                prev_duration = group_df.at[i-1, 'Mean_Duration_ms']
                curr_duration = group_df.at[i, 'Mean_Duration_ms']

                # Calculate percentage changes
                trial_pct_change = ((curr_trial - prev_trial) / prev_trial) * 100
                duration_pct_change = ((curr_duration - prev_duration) / prev_duration) * 100

                # Expected duration change equals trial_pct_change
                expected_change = trial_pct_change
                actual_change = duration_pct_change
                difference = abs(actual_change - expected_change)

                if difference > tolerance:
                    discrepancies.append({
                        'Function': func,
                        'Run_Group': group,
                        'Previous_Trial_Count': prev_trial,
                        'Current_Trial_Count': curr_trial,
                        'Trial_Count_Pct_Change': trial_pct_change,
                        'Mean_Duration_Pct_Change': duration_pct_change,
                        'Difference': difference
                    })

    return discrepancies

def save_discrepancies(discrepancies, output_file='accuracy_discrepancies.csv'):
    """
    Saves the discrepancies to a CSV file.

    Args:
        discrepancies (list): List of discrepancy dictionaries.
        output_file (str): Output CSV file name.
    """
    if discrepancies:
        discrepancy_df = pd.DataFrame(discrepancies)
        discrepancy_df = discrepancy_df[['Function', 'Run_Group', 'Previous_Trial_Count', 'Current_Trial_Count',
                                         'Trial_Count_Pct_Change', 'Mean_Duration_Pct_Change', 'Difference']]
        discrepancy_df.to_csv(output_file, index=False)
        print(f"\nDiscrepancies have been saved to '{output_file}'")
    else:
        print("\nNo discrepancies found. All configurations meet the desired accuracy.")

def main():
    parser = argparse.ArgumentParser(description='Check Accuracy of Benchmarking Results')
    parser.add_argument('csv_file', type=str, help='Path to the benchmarking CSV file')
    parser.add_argument('--confidence', type=float, default=0.95, help='Confidence level (default: 0.95)')
    parser.add_argument('--desired_moe', type=float, default=5, help='Desired Margin of Error percentage (default: 5)')
    parser.add_argument('--tolerance', type=float, default=5, help='Tolerance for proportionality check in percentage (default: 5)')
    args = parser.parse_args()

    # Load Data
    df = load_data(args.csv_file)

    # Preprocess Data
    df = preprocess_data(df)

    # Group Similar Runs
    df = group_similar_runs(df)

    # Assess Accuracy
    df = assess_accuracy(df, confidence_level=args.confidence, desired_moe=args.desired_moe)

    # Analyze Proportionality
    discrepancies = analyze_proportionality(df, tolerance=args.tolerance)

    # Print Summary
    print("\nAccuracy Assessment Summary:")
    summary = df.groupby(['Function']).agg(
        Total_Configs=('Mean_Duration_ms', 'count'),
        Meets_MOE=('Meets_Desired_MOE', 'sum')
    ).reset_index()
    summary['Meets_MOE_Percentage'] = (summary['Meets_MOE'] / summary['Total_Configs']) * 100
    print(summary)

    # Report Discrepancies
    if discrepancies:
        print(f"\nDiscrepancies Found: {len(discrepancies)}")
    else:
        print("\nNo discrepancies found. All configurations meet the desired accuracy.")

    # Save Discrepancies
    save_discrepancies(discrepancies)

if __name__ == "__main__":
    from scipy import stats
    main()
