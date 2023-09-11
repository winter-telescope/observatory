// Function to create and populate boxes
function createAndPopulateBoxes(data) {
    const container = document.getElementById('box-container');
    container.innerHTML = ''; // Clear existing content

    for (const columnKey in data) {
        if (data.hasOwnProperty(columnKey)) {
            const columnData = data[columnKey];

            for (const boxKey in columnData) {
                if (columnData.hasOwnProperty(boxKey)) {
                    const boxData = columnData[boxKey];
                    const boxDiv = document.createElement('div');
                    boxDiv.classList.add('box');

                    const header = document.createElement('h3');
                    header.textContent = boxData.header;
                    boxDiv.appendChild(header);

                    for (const key in boxData) {
                        if (key !== 'header' && boxData.hasOwnProperty(key)) {
                            const keyValue = document.createElement('p');
                            keyValue.textContent = `${key}: ${boxData[key]}`;
                            boxDiv.appendChild(keyValue);
                        }
                    }

                    container.appendChild(boxDiv);
                }
            }
        }
    }
}

// Function to fetch data from Flask app
function fetchData() {
    fetch('/get_data')
        .then(response => response.json())
        .then(data => {
            createAndPopulateBoxes(data);
        })
        .catch(error => {
            console.error('Error fetching data:', error);
        });
}

// Call the fetchData function on page load
document.addEventListener('DOMContentLoaded', () => {
    fetchData();
});
