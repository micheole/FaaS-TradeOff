import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
from sklearn.linear_model import LinearRegression
import numpy as np
from matplotlib.ticker import FuncFormatter

def plot_and_save_data(input_file, output_plot_file):
    """
    Plots mean durations with confidence intervals for two instances and adds regression lines.
    Ensures regression lines for each instance start from the mean value of the first run.
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

    # Ensure 'Num' is treated as a numeric variable for plotting
    df['Num'] = df['Num'].astype(int)

    # Create a formatted Num for x-axis labels (optional, for display only)
    df['Formatted_Num'] = df['Num'].apply(lambda x: f"{x:,}".replace(",", "."))

    # Sort the DataFrame by 'Num' and 'Instance' for consistency
    df = df.sort_values(['Num', 'Instance'])

    # Set the aesthetic style of the plots
    sns.set(style="whitegrid")

    # Get unique providers
    providers = df['Provider'].unique()

    # Initialize the FacetGrid
    g = sns.FacetGrid(df, col="Provider", hue="Instance", height=6, aspect=1.5, palette="tab10", legend_out=False)

    count = 0

    # Iterate over each facet (provider)
    for ax, provider in zip(g.axes.flat, providers):
        subset = df[df['Provider'] == provider].sort_values('Num')

        # Plot error bars for each instance
        for instance, color in zip(['Instance 1', 'Instance 2'], ['blue', 'green']):
            instance_subset = subset[subset['Instance'] == instance]
            ax.errorbar(
                instance_subset['Num'],
                instance_subset['Mean_Duration_ms'],
                yerr=[
                    instance_subset['Mean_Duration_ms'] - instance_subset['CI_Lower_ms'],
                    instance_subset['CI_Upper_ms'] - instance_subset['Mean_Duration_ms']
                ],
                fmt='o',
                capsize=5,
                color=color,
                label=f"{instance} (95% CI)"
            )

            # Add regression lines for each instance starting from the first point
            if len(instance_subset) > 1:
                # Get the first point
                first_x = instance_subset['Num'].iloc[0]
                first_y = instance_subset['Mean_Duration_ms'].iloc[0]
                num_runs = instance_subset['Num_Runs'].iloc[0]

                # Linear regression calculation
                X = instance_subset['Num'].values.reshape(-1, 1)
                y = instance_subset['Mean_Duration_ms'].values

                # Perform regression and adjust to pass through the first point
                reg = LinearRegression()
                reg.fit(X, y)

                # Recompute intercept to ensure the line passes through the first point
                slope = reg.coef_[0]
                intercept = first_y - slope * first_x

                # Generate regression line
                X_pred = np.linspace(instance_subset['Num'].min(), instance_subset['Num'].max(), 100)
                y_pred = slope * X_pred + intercept

                # Plot the adjusted regression line
                ax.plot(
                    X_pred,
                    y_pred,
                    linestyle='--',
                    color=color,
                    label=f"{instance} Regression ({num_runs} Runs)"
                )
                # if count % 2 == 0:
                #     ax.plot(
                #         X_pred,
                #         y_pred,
                #         linestyle='--',
                #         color=color,
                #         label=f"{instance} Regression (Afternoon)"
                #     )
                # elif count % 2 != 0:
                #     ax.plot(
                #         X_pred,
                #         y_pred,
                #         linestyle='--',
                #         color=color,
                #         label=f"{instance} Regression (Evening)"
                #     )
                count += 1

        # Calculate theoretical durations based on O(n log(log(n)))
        first_num = subset['Num'].iloc[0]
        first_mean_duration = subset['Mean_Duration_ms'].iloc[0]
        theoretical_durations = [
            first_mean_duration * (n * np.log(np.log(n))) / (first_num * np.log(np.log(first_num))) if n > 1 else first_mean_duration
            for n in subset['Num']
        ]

        

        # Set title
        num_runs = subset['Num_Runs'].iloc[0]
        ax.set_title(f"Sieve of Eratosthenes: {num_runs} runs")

        # Customize x-axis labels with thousand separators
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{int(x):,}".replace(",", ".")))

        # Rotate x-axis labels for better readability
        plt.setp(ax.get_xticklabels(), rotation=45)

        # Add legend
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys())

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