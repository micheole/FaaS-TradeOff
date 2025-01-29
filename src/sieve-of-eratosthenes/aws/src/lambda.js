exports.handler = async (event, context) => {
    let uniqueId = context.awsRequestId;

    const querynum = event.queryStringParameters && event.queryStringParameters.num
        ? parseInt(event.queryStringParameters.num, 10)
        : null;

    const body = event.body ? JSON.parse(event.body) : {};
    const bodynum = body.num && parseInt(body.num, 10) > 0
        ? parseInt(body.num, 10)
        : null;

    let num = querynum || bodynum;
    
    // Execute the Sieve of Eratosthenes to find primes
    let primes = sieveOfEratosthenes(num);

    return {
        statusCode: 200,
        body: JSON.stringify({
            uniqueId: uniqueId,
            primes: primes,
            num: num
        }),
        headers: {
            'Content-Type': 'application/json'
        }
    };
};

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
