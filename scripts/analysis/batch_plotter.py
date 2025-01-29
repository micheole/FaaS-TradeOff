import os
import subprocess
import argparse

def run_plotter(processed_logs_dir, output_plots_dir, plotter_script):
    """
    Runs the plotter script for all processed logs in the specified directory.

    Args:
        processed_logs_dir (str): Directory containing the processed log CSV files.
        output_plots_dir (str): Directory to save the generated plot files.
        plotter_script (str): Path to the plotter script.

    Example:
        python3 batch_plotter.py --processed_logs_dir ../../reports/processed-logs/gcp --output_plots_dir ../../reports/plots/gcp --plotter_script plot_confidence_intervals.py    
    """
    # Ensure the output directory exists
    os.makedirs(output_plots_dir, exist_ok=True)

    # Walk through the processed logs directory
    for root, _, files in os.walk(processed_logs_dir):
        for file in files:
            if file.endswith('.csv'):
                # Full path to the input processed log file
                input_file = os.path.join(root, file)
                
                # Generate the output plot filename
                filename_without_ext = os.path.splitext(file)[0]
                plot_filename = f"plot_{filename_without_ext}.svg"
                output_file = os.path.join(output_plots_dir, plot_filename)
                
                # Construct the command to run the plotter script
                command = [
                    "python3",
                    plotter_script,
                    "--input_file", input_file,
                    "--output_plot_file", output_file
                ]
                
                # Run the plotter script
                print(f"Generating plot for: {input_file}")
                subprocess.run(command, check=True)
                print(f"Plot saved to: {output_file}")

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Batch plot generator for processed logs.")
    parser.add_argument('--processed_logs_dir', type=str, required=True, help='Directory containing processed log files.')
    parser.add_argument('--output_plots_dir', type=str, required=True, help='Directory to save the generated plots.')
    parser.add_argument('--plotter_script', type=str, required=True, help='Path to the plotter script.')
    args = parser.parse_args()

    # Run the plotter for all processed logs
    run_plotter(args.processed_logs_dir, args.output_plots_dir, args.plotter_script)

if __name__ == "__main__":
    main()
