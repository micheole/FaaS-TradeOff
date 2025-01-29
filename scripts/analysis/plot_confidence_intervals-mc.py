import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse

def plot_and_save_data(input_file, output_plot_file):
    """
    Plots mean durations with confidence intervals and saves the plot and data to files.

    Args:
        input_file (str): Path to the input CSV file containing processed log data.
        output_plot_file (str): Path to the output image file for the plot.

    Example for running this:
        python(3) plot_confidence_intervals.py --input_file processed_logs.csv --output_plot_file output_plot.png
    """
    # Load the processed logs
    df = pd.read_csv(input_file)

    # Ensure Trial_Count is treated as a categorical variable for better plotting
    df['Trial_Count'] = df['Trial_Count'].astype(int)  # Treat as numeric for calculation

    # Format Trial_Count with a thousands separator
    df['Formatted_Trial_Count'] = df['Trial_Count'].apply(lambda x: f"{x:,}".replace(",", "."))


    df['Legend_Label'] = df['Provider'].str.upper() + " (95% CI)"
    trial_counts = df['Trial_Count'].sort_values().unique()  # Unique sorted trial counts

    # Calculate the theoretical regression line
    # first_mean_duration = df[df['Trial_Count'] == trial_counts[0]]['Mean_Duration_ms'].iloc[0]
    # theoretical_durations = [first_mean_duration * (1 + 0.05 * (i - 1)) for i in range(1, len(trial_counts) + 1)]
    # theoretical_df = pd.DataFrame({'Trial_Count': trial_counts, 'Theoretical_Duration': theoretical_durations})
    # Calculate the theoretical regression line
    trial_counts = df['Trial_Count'].sort_values().unique()  # Unique sorted trial counts
    first_mean_duration = df[df['Trial_Count'] == trial_counts[0]]['Mean_Duration_ms'].iloc[0]
    theoretical_durations = [first_mean_duration * (1 + 0.05 * (i - 1)) for i in range(1, len(trial_counts) + 1)]
    theoretical_df = pd.DataFrame({'Trial_Count': trial_counts, 'Theoretical_Duration': theoretical_durations})
    theoretical_df['Formatted_Trial_Count'] = theoretical_df['Trial_Count'].apply(lambda x: f"{x:,}".replace(",", "."))


    # Merge theoretical data for plotting
    # df['Trial_Count'] = df['Trial_Count'].astype(str)
    # theoretical_df['Trial_Count'] = theoretical_df['Trial_Count'].astype(str)

    # Set the aesthetic style of the plots
    sns.set(style="whitegrid")

    # Create a FacetGrid to plot AWS and GCP separately
    g = sns.FacetGrid(df, col="Provider", hue="Legend_Label", height=6, aspect=1, legend_out=False)

    # Map the data to the grid
    g = g.map(plt.errorbar, "Formatted_Trial_Count", "Mean_Duration_ms", 
              yerr=(df['Mean_Duration_ms'] - df['CI_Lower_ms'], df['CI_Upper_ms'] - df['Mean_Duration_ms']),
              fmt='o', capsize=5, linestyle='none')

    # Add the theoretical regression line to the plot
    for ax, provider in zip(g.axes.flat, df['Provider'].unique()):
        subset_theoretical = theoretical_df.copy()
        ax.plot(subset_theoretical['Formatted_Trial_Count'], subset_theoretical['Theoretical_Duration'], 
                linestyle='--', color='red', label='Theoretical Regression (5%)')

        ax.legend()
        # Get the first number of runs for the provider
        num_runs = df[df['Provider'] == provider]['Num_Runs'].iloc[0]

        ax.set_title(f"Monte-Carlo: {num_runs} runs")

    # Add titles and axis labels
    g.set_axis_labels("Trial Count", "Mean Duration (ms)")
    # g.set_titles("Monte-Carlo: {num_runs} run")

    # Rotate x-axis labels for better readability
    for ax in g.axes.flat:
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45)

    plt.tight_layout()

    # Save the plot to a file
    plt.savefig(output_plot_file)
    print(f"Plot saved to {output_plot_file}")

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Plot mean durations with confidence intervals and save the results.")
    parser.add_argument('--input_file', type=str, required=True, help='Path to the input CSV file.')
    parser.add_argument('--output_plot_file', type=str, required=True, help='Path to the output image file.')
    args = parser.parse_args()

    # Call the plotting and saving function
    plot_and_save_data(args.input_file, args.output_plot_file)

if __name__ == "__main__":
    main()
