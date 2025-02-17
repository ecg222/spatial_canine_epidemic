## Getting Started

This project uses publicly available data from NYC to inform the density of dogs in each zipcode.  

To access shapefiles for NYC zipcodes, go to [NYC's OpenData website](https://opendata.cityofnewyork.us/) and search for Modified Zip Code Tabulation Areas (MODZCTA)

To access dog license data for NYC, go to [NYC's OpenData website](https://opendata.cityofnewyork.us/) and search or NYC Dog Licensing Dataset. 

This project uses [poetry](https://python-poetry.org/) to manage dependencies. Please ensure you have poetry working. 

After accessing data, please proceed to Setup.ipynb. Change the file paths in the second cell to point towards your local copy of the data. Run each of the cells in the notebook. 

Next, proceed to Infections.ipynb. Change the parameters in the third cell to your desired values and run each of the cells. Output will be put into a folder of your choosing, based on the paths you provide. 