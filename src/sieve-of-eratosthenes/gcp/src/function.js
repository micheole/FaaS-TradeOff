const functions = require('@google-cloud/functions-framework');

functions.http('sieveOfEratosthenes', (req, res) => {
    const traceId = req.header('X-Cloud-Trace-Context')?.split('/')[0] || 'unknown-trace-id';

    const queryNum = req.query.num ? parseInt(req.query.num, 10) : null;
    const bodyNum = req.body && req.body.num ? parseInt(req.body.num, 10) : null;

    let num = queryNum || bodyNum;

    // Execute the Sieve of Eratosthenes to find primes
    let primes = sieveOfEratosthenes(num);

    res.status(200).json({
        traceId: traceId,
        primes: primes,
        num: num
    });
});

// Sieve of Eratosthenes implementation
let sieveOfEratosthenes = (num) => {
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

    return primeNumbers;
};
