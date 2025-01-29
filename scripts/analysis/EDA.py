import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import argparse

"""
python EDA.py --aws_path ./aws_logs --gcp_path ./gcp_logs --output_dir ./eda_plots
"""

# Step 1: Load and Combine Data
def load_data(aws_directory, gcp_directory):
    """
    Load all CSV files from the specified AWS and GCP directories.
    """
    dataframes = []
    
    # Load AWS logs
    for file in os.listdir(aws_directory):
        if file.endswith(".csv"):
            file_path = os.path.join(aws_directory, file)
            df = pd.read_csv(file_path)
            df['Source_File'] = file  # Add the file name for context
            df['Provider'] = 'AWS'  # Explicitly tag as AWS
            dataframes.append(df)
            print(f"Loaded AWS file: {file_path}")
    
    # Load GCP logs
    for file in os.listdir(gcp_directory):
        if file.endswith(".csv"):
            file_path = os.path.join(gcp_directory, file)
            df = pd.read_csv(file_path)
            df['Source_File'] = file  # Add the file name for context
            df['Provider'] = 'GCP'  # Explicitly tag as GCP
            dataframes.append(df)
            print(f"Loaded GCP file: {file_path}")
    
    if not dataframes:
        print("No CSV files found in the specified directories.")
        return None
    
    combined_df = pd.concat(dataframes, ignore_index=True)
    return combined_df

# Step 2: Save Plots
def save_plot(fig, filename, output_dir):
    """
    Save the current plot to the specified directory.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    filepath = os.path.join(output_dir, filename)
    fig.savefig(filepath, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved plot: {filepath}")

# Step 3: Summary Statistics
def summary_statistics(df):
    print("\nSummary Statistics:")
    print(df.describe())
    print("\nProvider-wise Statistics:")
    print(df.groupby('Provider')['Mean_Duration_ms'].describe())

# Step 4: Visualize Distributions
def plot_distributions(df, output_dir):
    sns.set(style="whitegrid")
    
    # Distribution of mean durations
    fig = plt.figure(figsize=(12, 6))
    sns.histplot(df, x="Mean_Duration_ms", hue="Provider", kde=True, bins=20, palette="Set2")
    plt.title("Distribution of Mean Execution Durations by Provider")
    plt.xlabel("Mean Duration (ms)")
    plt.ylabel("Frequency")
    save_plot(fig, "distribution_mean_execution_durations.svg", output_dir)

    # Distribution by Num (input size)
    fig = plt.figure(figsize=(12, 6))
    sns.boxplot(data=df, x="Num", y="Mean_Duration_ms", hue="Provider", palette="Set2")
    plt.title("Mean Execution Duration by Input Size and Provider")
    plt.xlabel("Input Size (Num)")
    plt.ylabel("Mean Duration (ms)")
    plt.xticks(rotation=45)
    save_plot(fig, "boxplot_mean_execution_by_input.svg", output_dir)

# Step 5: Compare Providers (AWS vs GCP)
def compare_providers(df, output_dir):
    grouped = df.groupby(['Provider', 'Num']).agg({
        'Mean_Duration_ms': ['mean', 'std', 'count']
    }).reset_index()
    grouped.columns = ['Provider', 'Num', 'Mean', 'Std', 'Count']
    print("\nProvider Comparison:")
    print(grouped)

    fig = plt.figure(figsize=(12, 6))
    sns.lineplot(data=grouped, x="Num", y="Mean", hue="Provider", marker="o", palette="Set2")
    plt.title("Comparison of Mean Execution Durations by Provider")
    plt.xlabel("Input Size (Num)")
    plt.ylabel("Mean Duration (ms)")
    plt.xticks(rotation=45)
    save_plot(fig, "comparison_mean_execution_durations.svg", output_dir)

# Step 6: Confidence Interval Analysis
def plot_confidence_intervals(df, output_dir):
    df['CI_Width'] = df['CI_Upper_ms'] - df['CI_Lower_ms']

    # Plot CI width by provider and input size
    fig = plt.figure(figsize=(12, 6))
    sns.barplot(data=df, x="Num", y="CI_Width", hue="Provider", palette="Set2")
    plt.title("Confidence Interval Widths by Input Size and Provider")
    plt.xlabel("Input Size (Num)")
    plt.ylabel("CI Width (ms)")
    plt.xticks(rotation=45)
    save_plot(fig, "confidence_interval_widths.svg", output_dir)

# Step 7: Variance/Error Analysis
def plot_variance(df, output_dir):
    df['Variance'] = (df['CI_Width'] / 2) ** 2  # Approximation for variance based on CI width
    
    fig = plt.figure(figsize=(12, 6))
    sns.lineplot(data=df, x="Num", y="Variance", hue="Provider", marker="o", palette="Set2")
    plt.title("Variance of Execution Times by Provider and Input Size")
    plt.xlabel("Input Size (Num)")
    plt.ylabel("Variance (ms^2)")
    plt.xticks(rotation=45)
    save_plot(fig, "variance_execution_times.svg", output_dir)

# Main Function
def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="EDA for Benchmark Logs")
    parser.add_argument('--aws_path', type=str, required=True, help='Path to the directory containing AWS log CSV files.')
    parser.add_argument('--gcp_path', type=str, required=True, help='Path to the directory containing GCP log CSV files.')
    parser.add_argument('--output_dir', type=str, required=True, help='Path to the directory to save the plots.')
    args = parser.parse_args()
    
    # Load the data
    df = load_data(args.aws_path, args.gcp_path)
    if df is None:
        print("No data to process. Exiting.")
        return
    
    # Print summary statistics
    summary_statistics(df)

    # Plot distributions
    plot_distributions(df, args.output_dir)

    # Compare providers
    compare_providers(df, args.output_dir)

    # Plot confidence intervals
    plot_confidence_intervals(df, args.output_dir)

    # Plot variance
    plot_variance(df, args.output_dir)

if __name__ == "__main__":
    main()
