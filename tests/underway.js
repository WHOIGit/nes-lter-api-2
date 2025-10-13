console.log("Running Underway Test.");

const cruises = ["ar77", "en617", "hrs2303", "ae2426", "at46"];

const getCounts = { ar77: 8192, en617: 8228, hrs2303: 9896, ae2426: 8341, at46: 8410 };
const colCounts = { ar77: 40, en617: 128, hrs2303: 23, ae2426: 45, at46: 38 };
const times = {
    ar77: '2023-10-11/2023-10-13', en617: '2018-07-20/2018-07-23',
    hrs2303: '2023-04-29/2023-05-06', ae2426: '2024-11-03/2024-11-03',
    at46: '2022-02-21/2022-02-21'
}

async function getData(cruise) {
  try {
    const response = await fetch(`http://localhost:8000/api/underway/get/${cruise}`);
    if (!response.ok) {
      throw new Error('HTTP error ' + response.status);
      }

    const data = await response.text();

    const lines = data
          .split('\n')
          .map(line => line.trim())
          .filter(line => line.length > 0); 

    const expected = getCounts[cruise];

    if (lines.length === expected)
    {
        console.log(`${cruise} Underway Get test successful.`);
    }
    else {
        console.log(`${cruise} Underway are missing.`);
        console.log(`${cruise} Underway Get test failed.`);
    }
  } catch (err) {
      console.log(`${cruise} Underway Get test failed.`);
    console.error('Error:', err);
  }


  try {
      const response = await fetch(`http://localhost:8000/api/underway/get_column_headers/${cruise}`);
    if (!response.ok) {
        throw new Error('HTTP error ' + response.status);
    }
    const data = await response.json();
   
    const expected = colCounts[cruise];

    if (data.metadata.num_columns === expected) {
        console.log(`${cruise} Underway Get Column Headers test successful.`);
    } else {
        console.log(`${cruise} Underway Get Column Headers test failed.`);
      }
  } catch (err) {
      console.log(`${cruise} Underway Get Column Headers test failed.`);
      console.error('Error:', err);
  }

try {
    const search = times[cruise];
    const response = await fetch(`http://localhost:8000/api/underway/find/${search}`);
    if (!response.ok) {
        throw new Error('HTTP error ' + response.status);
    }
    const data = await response.json();

    if (data[0].file_name == `${cruise}_underway.csv`) {
        console.log(`${cruise} Underway Find test successful.`);
    } else {
        console.log(`${ cruise } Underway Find test failed.`);
    }

  } catch (err) {
     console.log(`${cruise} Underway Find test failed.`);
     console.log('Error:', err);
    }


}

async function runAll() {
    for (const cruise of cruises) {
        await getData(cruise);
    }
}

runAll();
