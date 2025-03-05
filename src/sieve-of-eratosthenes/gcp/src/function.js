const functions = require('@google-cloud/functions-framework');
var coldStart = true;

functions.http('sieveOfEratosthenes', (req, res) => {
  // Extract a unique request ID from the header (if available)
  const uniqueId = req.header('X-Cloud-Trace-Context')?.split('/')[0] || 'unknown-trace-id';

  // Cold start detection
  let markColdStart = false;
  if (coldStart) {
    coldStart = false;
    markColdStart = true;
  }

  // Retrieve the input parameter from query or body
  const queryNum = req.query.num ? parseInt(req.query.num, 10) : null;
  const bodyNum = req.body && req.body.num ? parseInt(req.body.num, 10) : null;
  let num = queryNum || bodyNum;

  // Validate the input: must be a number greater than 1
  if (!num || num <= 1) {
    res.status(400).json({
      error: "Please provide a valid input parameter greater than 1."
    });
    return;
  }

  // Execute the Sieve of Eratosthenes to compute primes
  let primes = sieveOfEratosthenes(num);

  res.status(200).json({
    uniqueId: uniqueId,
    num: num,
    markColdStart: markColdStart,
    // Optionally include the primes list if desired
    // primes: primes
  });
});

// Updated Sieve of Eratosthenes implementation
function sieveOfEratosthenes(trials) {
  // Create an array where each element starts as true
  const numsArr = Array.from({ length: trials + 1 }, () => true);

  // Loop from 2 to the square root of trials
  for (let i = 2; i <= Math.floor(Math.sqrt(trials)); i++) {
    if (numsArr[i]) {
      // Mark multiples of i as false
      for (let j = i + i; j <= trials; j += i) {
        numsArr[j] = false;
      }
    }
  }

  // Collect the prime numbers (ignoring indices 0 and 1)
  const primeNumbers = numsArr.reduce((result, element, index) => {
    if (element && index > 1) {
      result.push(index);
    }
    return result;
  }, []);

  return primeNumbers;
}
