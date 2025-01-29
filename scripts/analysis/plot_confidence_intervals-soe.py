import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import numpy as np
from matplotlib.ticker import FuncFormatter

def plot_and_save_data(input_file, output_plot_file):
    """
    Plots mean durations with confidence intervals and saves the plot and data to files.

    Args:
        input_file (str): Path to the input CSV file containing processed log data.
        output_plot_file (str): Path to the output image file for the plot.

    Example for running this:
        python plot_confidence_intervals.py --input_file processed_logs.csv --output_plot_file output_plot.png
    """
    # Load the processed logs
    df = pd.read_csv(input_file)

    # Ensure Num is treated as a numeric variable for calculation
    df['Num'] = df['Num'].astype(int)

    # Create a formatted Num for x-axis labels (optional, for display only)
    df['Formatted_Num'] = df['Num'].apply(lambda x: f"{x:,}".replace(",", "."))

    # Create a legend label combining Provider and CI info
    df['Legend_Label'] = df['Provider'].str.upper() + " (95% CI)"

    # Get unique providers
    providers = df['Provider'].unique()

    # Set the aesthetic style of the plots
    sns.set(style="whitegrid")

    # Initialize the FacetGrid
    g = sns.FacetGrid(df, col="Provider", hue="Legend_Label", height=6, aspect=1.5, legend_out=False)

    # Define a function to plot error bars and theoretical lines
    def plot_data(x, y, yerr, color, label, ax, theoretical_x, theoretical_y):
        ax.errorbar(x, y, yerr=yerr, fmt='o', capsize=5, label=label, color=color)
        ax.plot(theoretical_x, theoretical_y, linestyle='--', color='red', label='Theoretical (O(n log(log n)))')

    # Iterate over each facet (provider)
    for ax, provider in zip(g.axes.flat, providers):
        subset = df[df['Provider'] == provider].sort_values('Num')
        
        # Plot error bars
        ax.errorbar(
            subset['Num'],
            subset['Mean_Duration_ms'],
            yerr=[subset['Mean_Duration_ms'] - subset['CI_Lower_ms'], subset['CI_Upper_ms'] - subset['Mean_Duration_ms']],
            fmt='o',
            capsize=5,
            label=f"{provider.upper()} (95% CI)",
            color='blue'
        )
        
        # Calculate theoretical durations based on O(n log(log(n)))
        first_num = subset['Num'].iloc[0]
        first_mean_duration = subset['Mean_Duration_ms'].iloc[0]
        theoretical_durations = [
            first_mean_duration * (n * np.log(np.log(n))) / (first_num * np.log(np.log(first_num)))
            for n in subset['Num']
        ]
        
        # Plot theoretical regression line
        ax.plot(
            subset['Num'],
            theoretical_durations,
            linestyle='--',
            color='red',
            label='Theoretical (O(n log(log n)))'
        )
        
        # Set title
        num_runs = subset['Num_Runs'].iloc[0]
        ax.set_title(f"Sieve of Eratosthenes: {num_runs} runs")
        
        # Set x-axis to log scale if desired (optional)
        # ax.set_xscale('log')
        
        # Customize x-axis labels with thousand separators
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{int(x):,}".replace(",", ".")))
        
        # Rotate x-axis labels for better readability
        plt.setp(ax.get_xticklabels(), rotation=45)
        
        # Add legend
        ax.legend()

    # Set common axis labels
    g.set_axis_labels("Maximum Number (n)", "Mean Duration (ms)")

    # Adjust layout
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