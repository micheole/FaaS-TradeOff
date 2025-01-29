import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
from sklearn.linear_model import LinearRegression
import numpy as np
from matplotlib.ticker import FuncFormatter

def plot_and_save_data(input_file, output_plot_file):
    """
    Plots mean durations with confidence intervals for two instances and adds fixed regression lines.
    Ensures regression lines for each instance start from the mean value of the first run and grow linearly with a fixed 5% slope.
    Saves the plot to a file.

    Args:
        input_file (str): Path to the input CSV file containing processed log data.
        output_plot_file (str): Path to the output image file for the plot.
    """
    # Load the processed logs
    df = pd.read_csv(input_file)

    # Assign Instance based on alternating rows
    df = df.reset_index(drop=True)
    df['Instance'] = df.index.map(lambda x: 'Instance 1' if x % 2 == 0 else 'Instance 2')

    # Ensure Trial_Count is treated as a numeric variable for plotting
    df['Trial_Count'] = df['Trial_Count'].astype(int)

    # Format Trial_Count with a thousands separator
    df['Formatted_Trial_Count'] = df['Trial_Count'].apply(lambda x: f"{x:,}".replace(",", "."))

    # Sort the DataFrame by Trial_Count and Instance for consistency
    df = df.sort_values(['Trial_Count', 'Instance'])

    # Set the aesthetic style of the plots
    sns.set(style="whitegrid")

    # Initialize the matplotlib figure
    plt.figure(figsize=(12, 8))

    # Create a color palette
    palette = sns.color_palette("tab10", n_colors=df['Instance'].nunique())
    instance_colors = dict(zip(df['Instance'].unique(), palette))

    # Plot error bars for each instance using Matplotlib's plt.errorbar
    for instance, color in zip(df['Instance'].unique(), palette):
        subset = df[df['Instance'] == instance]
        plt.errorbar(
            subset['Trial_Count'],
            subset['Mean_Duration_ms'],
            yerr=[
                subset['Mean_Duration_ms'] - subset['CI_Lower_ms'],
                subset['CI_Upper_ms'] - subset['Mean_Duration_ms']
            ],
            fmt='o',
            capsize=5,
            color=color,
            label=f"{instance} (95% CI)"
        )

    # Add fixed 5% slope regression lines for each instance, starting from the first run's mean duration
    for instance, color in zip(df['Instance'].unique(), palette):
        subset = df[df['Instance'] == instance]
        if len(subset) > 0:
            # Get the first data point
            first_x = subset['Trial_Count'].iloc[0]
            first_y = subset['Mean_Duration_ms'].iloc[0]

            if first_x != 0:
                # Calculate fixed slope: 5% increase implies y increases proportionally to x
                slope_fixed = first_y / first_x
            else:
                slope_fixed = 0  # Avoid division by zero

            # Calculate intercept to ensure the line starts from the first data point
            intercept_fixed = first_y - slope_fixed * first_x

            # Generate regression line using the fixed slope
            X_pred = np.linspace(subset['Trial_Count'].min(), subset['Trial_Count'].max(), 100)
            y_pred_fixed = slope_fixed * X_pred + intercept_fixed

            # Plot the fixed regression line
            plt.plot(
                X_pred,
                y_pred_fixed,
                linestyle='--',
                color=color,
                label=f"{instance} Fixed 5% Regression"
            )

    # Add titles and axis labels
    plt.title("Mean Duration with 95% Confidence Intervals for Two Instances")
    plt.xlabel("Trial Count")
    plt.ylabel("Mean Duration (ms)")

    # Format x-axis with thousands separator and rotate labels
    plt.xticks(
        df['Trial_Count'].unique(),
        [f"{x:,}".replace(",", ".") for x in df['Trial_Count'].unique()],
        rotation=45
    )

    # Combine legends for error bars and regression lines
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys())

    # Adjust layout for better fit
    plt.tight_layout()

    # Save the plot to a file
    plt.savefig(output_plot_file)
    print(f"Plot saved to {output_plot_file}")

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Plot mean durations with confidence intervals for two instances and save the plot.")
    parser.add_argument('--input_file', type=str, required=True, help='Path to the input CSV file.')
    parser.add_argument('--output_plot_file', type=str, required=True, help='Path to the output image file.')
    args = parser.parse_args()

    # Call the plotting and saving function
    plot_and_save_data(args.input_file, args.output_plot_file)

if __name__ == "__main__":
    main()
