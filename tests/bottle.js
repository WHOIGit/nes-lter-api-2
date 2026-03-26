console.log("Running Bottle Test.");

const cruises = ["ar77", "en617", "hrs2303", "ae2426", "at46"];

const lineCounts = { ar77: 310, en617: 359, hrs2303: 145, ae2426: 266, at46: 305 };

var myArgs = process.argv.slice(2);

async function getData(cruise) {
  try {

      if (myArgs[0] == 'public') {
          url = `https://nes-lter-api.whoi.edu`;
      }
      else {
          url = `http://localhost:8000`;
      }

    const response = await fetch(`${url}/api/ctd/bottles/${cruise}.csv`);

    if (!response.ok) {
      throw new Error('HTTP error ' + response.status);
      }

    const data = await response.text();

    const lines = data
          .split('\n')
          .map(line => line.trim())
          .filter(line => line.length > 0); 

    const expected = lineCounts[cruise];

    if (lines.length === expected) 
    {
        console.log(`${cruise} Bottles Get All test successful.`);
    }
    else {
        console.log(`${cruise} Bottles for All are missing.`);
        console.log(`${cruise} Bottles Get All test failed.`);
    }
  } catch (err) {
      console.log(`${cruise} Bottles Get All test failed.`);
    console.error('Error:', err);
  }


  try {

    response = await fetch(`${url}/api/ctd/bottle_summary/${cruise}.csv`);

    if (!response.ok) {
        throw new Error('HTTP error ' + response.status);
    }
    const data = await response.text();
   
    const lines = data
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0);

    const expected = lineCounts[cruise];

    if (lines.length === expected) { 
        console.log(`${cruise} Bottle Summary test successful.`);
    } else {
        console.log(`${cruise} Bottle Summary test failed.`);
    }

  } catch (err) {
      console.log(`${cruise} Bottle Summary test failed.`);
     console.error('Error:', err);
  }
}

async function runAll() {
    for (const cruise of cruises) {
        await getData(cruise);
    }
}

runAll();
