# Universal Iramuteq Tagger

A Streamlit-based application for academic abstract classification that leverages OpenAI API for intelligent tag classification and data export.

## Project Structure

```
├── .streamlit/
│   ├── config.toml    # Streamlit configuration
│   └── secrets.toml   # OpenAI API key storage
├── main.py            # Main Streamlit application
├── styles.css         # Custom styling
└── README.md         # This file
```


## Features

- Upload Excel files containing academic abstracts
- Configure custom tags and subtags for classification
- OpenAI-powered automatic classification
- Export results in Excel and Iramuteq-compatible formats
- Customizable tag definitions

## Setup Instructions

1. Ensure you have an OpenAI API key
2. Configure your API key in one of three ways:
   - Create `apikeys.py` with `openai = "your-api-key"`
   - Add to `.streamlit/secrets.toml`: `openai_api_key = "your-api-key"`
   - Enter directly in the application interface

## Required Excel File Format

Your Excel file should contain the following columns:
- paper title
- publication year
- journal
- abstract

## Usage

1. Enter your OpenAI API key
2. Upload your Excel file
3. Define your study objective
4. Configure custom tags and their possible values
5. Process the abstracts
6. Download results in Excel and Iramuteq formats

## Dependencies

- streamlit
- pandas
- openai
- openpyxl
- rapidfuzz
