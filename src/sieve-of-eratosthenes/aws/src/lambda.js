var coldStart = true;

exports.handler = async (event, context) => {
  const uniqueId = context.awsRequestId;

  // Cold start detection
  let markColdStart = false;
  if (coldStart) {
    coldStart = false;
    markColdStart = true;
  }

  // Retrieve the input parameter from query parameters or request body
  const querynum = event.queryStringParameters && event.queryStringParameters.num
    ? parseInt(event.queryStringParameters.num, 10)
    : null;
  const body = event.body ? JSON.parse(event.body) : {};
  const bodynum = body.num && parseInt(body.num, 10) > 0
    ? parseInt(body.num, 10)
    : null;
  let num = querynum || bodynum;

  // If no valid number is provided, return an error.
  if (!num || num <= 1) {
    return {
      statusCode: 400,
      body: JSON.stringify({ error: "Please provide a valid input parameter greater than 1." }),
      headers: { "Content-Type": "application/json" }
    };
  }

  // Execute the Sieve of Eratosthenes to find primes using the new implementation
  let primes = sieveOfEratosthenes(num);

  return {
    statusCode: 200,
    body: JSON.stringify({
      uniqueId: uniqueId,
      num: num,
      markColdStart: markColdStart,
      // Optionally include the primes list (commented out if not needed)
      // primes: primes 
    }),
    headers: { "Content-Type": "application/json" }
  };
};

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

  // Collect the prime numbers
  const primeNumbers = numsArr.reduce((result, element, index) => {
    if (element && index > 1) {
      result.push(index);
    }
    return result;
  }, []);

  return primeNumbers;
}
