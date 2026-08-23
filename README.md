# 🌱 ELRF WhatsApp Monitoring Data Extractor

## Data Extraction + Automation

A Python and Streamlit-based data extraction system designed to convert unstructured WhatsApp monitoring reports from mangrove restoration field teams into a structured dataset ready for analysis, reporting, and monitoring.

---

## 📌 Project Overview

Field monitoring teams often submit restoration and survival monitoring information through WhatsApp messages.

These reports can contain:

- Different reporting formats
- Inconsistent spelling
- Different date formats
- Multiple planting sessions
- Multiple monitoring plots
- Species abbreviations
- Missing or differently labelled fields
- Mixed text and numerical information

Manually transferring this information into spreadsheets is time-consuming and can introduce errors.

This system automates the extraction and standardization process.

### Workflow

WhatsApp Report  
↓  
Text Parsing & Pattern Recognition  
↓  
Data Cleaning & Standardization  
↓  
Structured Monitoring Dataset  
↓  
Data Quality Checks  
↓  
Excel Export  
↓  
Analysis & Reporting

---

## 🎯 Objectives

The system was developed to:

- Automate extraction of monitoring data from WhatsApp reports
- Reduce manual data entry
- Standardize field monitoring information
- Handle variations in reporting formats
- Calculate tree age automatically
- Separate replanted and old surviving trees
- Validate monitoring records
- Produce structured datasets for analysis
- Export cleaned data to Excel

---

## ⚙️ Key Features

### 1. WhatsApp Report Extraction

The system accepts raw WhatsApp monitoring reports and extracts structured information such as:

- County
- Planting site
- Monitoring check
- Plot number
- Monitoring date
- Planting date
- Planting session ID
- Species planted
- Planting material
- Number of trees planted
- Area restored
- Coordinates
- Tree survival observations
- Mortality
- Dormant trees
- Natural regeneration
- Tree age
- Spacing
- Zonation
- Disturbances
- Recommendations
- Comments

---

### 2. Data Standardization

The parser handles common variations in field reporting.

For example, species abbreviations such as:

- `CT`
- `C.T`
- `C.tagal`
- `Ceriops tagal`

are standardized to:

`Ceriops tagal`

Similar standardization is applied to other mangrove species.

---

### 3. Automated Tree Age Calculation

Tree age is calculated from the planting date and monitoring date.

Example:

```text
Planting date: 18 May 2025
Monitoring date: 21 August 2026

Tree age: 1 year