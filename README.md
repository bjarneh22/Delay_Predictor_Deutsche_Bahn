# DL4Y C4$H

<img src="DC_Logo.png" alt="logo" width="200"/>

An application that predicts future delays of train connections in Germany. Based on these predictions, the application provides an overview of adjusted prices for the connections, calculated according to the refund rules of the DB (Deutsche Bahn - German Railway).

----
## Description

Many train travelers in Germany face frequent delays and often do not reach their destination on time. However, for some travelers, the primary concern is not the delay itself but the rising ticket prices of Deutsche Bahn.

This application helps train travelers by providing adjusted prices for train connections based on predicted delays. If a train exceeds a certain delay threshold, travelers can get refunds from DB according to their compensation rules. The app therefore enables users to make informed and cost-efficient travel decisions.

In a first step, the required data is imported. After cleaning the data, previously trained machine learning algorithms are applied to predict the delay for the train connection. The results are display in a web app and users can retrieve detailed information on the prediction.

----
## Functionalities

### Data Sources and Retrieval

Data is collected in a hybrid manner
   1. For the collection of the historical data we use an open dataset https://piebro.github.io/deutsche-bahn-statistics
     - Used for training a model to recognize delay patterns and do exploratory analysis on 
   2. For the collection of the live data we use an API https://v6.db.transport.rest/api.html
     - Provides information on current trains which the model can make predictions on

After collecting the relevant data, it will be checked to ensure quality and correctness.

Libraries that are required for this step are 
  1. requests
  2. pandas & datasets
  3. duckdb
      
### Data Storage and Handling

**Storage**  
Our project uses a hybrid storage approach, depending on the type of data:
   1. Train data
      - We use a DuckDB database as the primary storage system.
      - Allows structured storage of train, station, and delay data
      - Supports efficient queries for filtering, sorting, joining, and aggregation
      - Required package: duckdb

**Handling**  
To load, process, and analyze our data, we use several Python libraries:
   1. NumPy: Used for numerical operations.
   2. Pandas: Used for tabular data handling, transformations, and preparing data for visualizations.
   3. Lambda functions: Used for filtering and sorting operations.

This combination allows us to handle incoming API data, transform it, store it, and later analyse it for visualizations and reporting.

### Interface

**Web app with streamlit**  
We build a web app with streamlit with the corresponding streamlit package.

The app will integrate with the other libraries used throughout the project, including:
- pandas for data manipulation, analysis and database access
- joblib to load our models

This approach ensures a seamless connection between our data storage, analysis, and user-facing interface.

### Statistical Analysis

In order to generate reliable predictions for future train delays, we apply a combination of exploratory data analysis (EDA), feature engineering, and machine learning evaluation techniques.

**Data Cleaning**  
Data cleaning includes filtering the data, selecting relevant cases, and handling missing values (using **pandas** and **numpy**).

**Exploratory Data Analysis (EDA)**  
Before modeling, the dataset will be examined to get an impression of the data, detect anomalies, and identify relevant correlations. This includes for example:  
- Descriptive statistics (using **pandas**, **numpy**)  
- Correlation analysis (using **pandas**, **scipy**)  
- Visual analysis (using **matplotlib**)  

**Feature Engineering**  
Based on EDA results, features influencing the delay of a train will be constructed or transformed. Examples include:  
- Aggregated historical data on train delays  
- Derived weather indicators for a given time frame  
- Categorization of variables  
Feature engineering will be supported by **pandas**, **numpy**, and model-preprocessing tools from **scikit-learn**.

**Modeling and Evaluation**  
The application uses Gradient Boosting to predict expected delays or probabilities of surpassing a certain delay threshold.  
The model performance will be evaluated with appropriate statistical metrics, such as:  
- Mean Absolute Error
- Cross-validation  
These models will be implemented and tested with **scikit-learn**.

**Application**  
These models are then applied to data selected by users (specific train connections). Uncertainty measures, such as prediction intervals for point estimates or classification probabilities, can also be displayed in the web app. Users will be able to access information about the model and download the results as a TXT file.

----
### Table for self-check

| Category                     | Details                                                                           | Mark with ✔️ |
|:-----------------------------|:----------------------------------------------------------------------------------|--------------|
| 1. Source                    | High-quality dataset                                                              |     ✔️      |
|                              | Quality control / cleaning                                                        |     ✔️      |
| 2. Data Storage and Handling | Management system                                                                 |     ✔️       |
|                              | No plaintext passwords                                                            |     ✔️        |
| 3. Interface                 | CLI, GUI or Web interface for users                                               |     ✔️       |
|                              | Extensive interface functions (account management, queries, analysis, help)       |     ✔️        |
| 4. Statistical Analysis      | Interactive statistics area                                                       |              |
|                              | Basic statistics                                                                  |     ✔️        |
| Always mandatory             | Project proposal with incorporated feedback from tutor                            |     ✔️       |
|                              | GitHub repo with sensible commit messages, template README, contributions section |     ✔️       |
|                              | Frequent commenting                                                               |     ✔️       |
|                              | Docstrings for every function/class                                               |            |
|                              | Testing of relevant functionalities to avoid crashing                             |            |
|                              | Help page for system                                                              |            |
|                              | Milestone presentation                                                            |     ✔️       |
|                              | AI-Usage Cards                                                                    |            |

----
## How to Install

1. Clone the repository:
   git clone https://github.com/bjarneh22/TBA_project.git
   cd TBA_project

2. Create a virtual environment:
   python -m venv venv
   source venv/bin/activate

3. Install dependencies:
   pip install -r requirements.txt

4. Run the project:
   streamlit run streamlit_app_dummy.py

----
## How to Use

1. Follow the instructions in the **Installation** section.

2. Once the application opens in your browser, select your **departure station**.

3. Choose one of the available **destination stations** from the dropdown menu.

4. Enter the **ticket price** you paid for your journey.

5. Click **"Calculate Prediction"**.

6. The application will display the **expected delay**, including best-case and worst-case scenarios.

7. Optionally, download a delay prediction report as a `.txt` file by clicking **"Download Report (TXT)"** under **Export Results**.


----
## Timeline

| Task             | 11/24/2025 | 12/01/2025 | 12/08/2025 | 12/15/2025 | 01/05/2026 | 01/12/2026 | 01/19/2026 | 01/26/2026 | 02/02/2026 | 02/09/2026 |
|-----------------|:----------:|:----------:|:----------:|:----------:|:----------:|:----------:|:----------:|:----------:|:----------:|:----------:|
| Data Gathering  | X          | X          | X          | X          |            |            |            |            |            |            |
| Data Cleaning   |            | X          | X          | X          | X          | X          |            |            |            |            |
| Analysis        |            |            | X          | X          | X          | X          | X          |            |            |            |
| UI Design       |            |            |            |            | X          | X          | X          | X          | X          |            |
| Refactoring     |            |            |            |            |            | X          | X          |            |            |            |
| Presentation    |            |            |            |            | X          | X          | X          | X          | X          | X          |

----
## Group Details

Group information:
- Group name: TBA 
- Group code: G08
- Group repository: https://github.com/bjarneh22/TBA_project
- Tutor responsible: Constantin Dallinghaus 
- Group team leader: Jakob Erhard (jakob.erhard01@stud.uni-goettingen.de)
- Group members: Jakob Erhard, Bjarne Herbst, Eduard Unruh

Contribution of each group member:

**Jakob Erhard (Data Analysis)**: Development, implementation, and testing of machine learning models

**Bjarne Herbst (Backend & API)**: Data collection and implementation of required API calls

**Eduard Unruh (Storage & Data Management)**: Design and implementation of data storage, including database structure, management of train data, and ensuring efficient data processing and access

**All (Frontend & UI)**: Development of the web application, including user interface design and integration of statistical results.


----
## Acknowlegdments

### Libraries
- requests
- numpy
- matplotlib
- pandas
- streamlit
- holidays
- ipykernel
- duckdb
- scikit-learn
- nbformat
- seaborn
- statsmodels
- sklearn-quantile

### Inspirations and Similar Projects
- https://bahnvorhersage.de/
- https://piebro.github.io/deutsche-bahn-statistics

### References
- tbd
- tbd
