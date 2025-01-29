const { performance } = require('perf_hooks'); // Import performance for timing
const stats = require('simple-statistics'); // Install this library for confidence intervals

// Function to execute the Sieve of Eratosthenes and measure duration
const sieveOfEratosthenes = (num) => {
    const startTime = performance.now(); // Start timing

    // Create a boolean array to mark primes
    let prime = Array(num + 1).fill(true);
    let p = 2;

    while (p * p <= num) {
        // If prime[p] is still true, it's a prime
        if (prime[p]) {
            // Mark all multiples of p as not prime
            for (let i = p * p; i <= num; i += p) {
                prime[i] = false;
            }
        }
        p++;
    }

    // Collect all prime numbers
    let primeNumbers = [];
    for (let p = 2; p <= num; p++) {
        if (prime[p]) {
            primeNumbers.push(p);
        }
    }

    const endTime = performance.now(); // End timing
    const duration = endTime - startTime; // Calculate duration in milliseconds

    return { primes: primeNumbers, duration }; // Return primes and duration
};

// Function to simulate 1000 runs asynchronously
const simulateRuns = async (num, iterations) => {
    console.log(`Simulating ${iterations} runs for num=${num}...`);
    const durations = [];

    for (let i = 0; i < iterations; i++) {
        const { duration } = sieveOfEratosthenes(num);
        durations.push(duration);

        // Log progress every 100 iterations
        if ((i + 1) % 100 === 0) {
            console.log(`Completed ${i + 1} iterations...`);
        }
    }

    // Calculate mean and 95% confidence intervals
    const meanDuration = stats.mean(durations);
    const stdError = stats.standardDeviation(durations) / Math.sqrt(durations.length);
    const marginOfError = 1.96 * stdError; // 95% confidence interval
    const ciLower = meanDuration - marginOfError;
    const ciUpper = meanDuration + marginOfError;

    console.log(`Results for num=${num}, iterations=${iterations}`);
    console.log(`Mean Duration: ${meanDuration.toFixed(2)} ms`);
    console.log(`95% Confidence Interval: (${ciLower.toFixed(2)}, ${ciUpper.toFixed(2)})`);
};

// Main function to run multiple test cases
const main = async () => {
    const testCases = [
        { num: 1000000, iterations: 1000 }, // Run 1000 tests for 1,000,000
        { num: 1050000, iterations: 1000 }, // Run 1000 tests for 1,050,000
        { num: 1102500, iterations: 1000 }, // Run 1000 tests for 1,102,500
        { num: 1157625, iterations: 1000 }, // Run 1000 tests for 1,157,625
    ];

    for (const testCase of testCases) {
        await simulateRuns(testCase.num, testCase.iterations);
    }
};

main();
