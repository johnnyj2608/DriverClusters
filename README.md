# 🚐 Route Optimization & Member Scheduling System

## 📑 Table of Contents

1. [Overview](#overview)
2. [Tech Stack](#tech-stack)
3. [Key Features](#key-features)
   - [General](#general)
   - [Template Upload System](#template-upload-system)
   - [Scheduling Inputs](#scheduling-inputs)
   - [Wedge-Based Clustering](#wedge-based-clustering)
   - [Routing & Optimization](#routing--optimization)
   - [Traffic-Aware Travel Time Simulation](#traffic-aware-travel-time-simulation)
   - [Output System](#output-system)
4. [System Architecture](#system-architecture)
5. [Challenges & Lessons Learned](#challenges--lessons-learned)

---

<a name="overview"></a>
## 📖 Overview

This project is a **Tkinter-based route optimization and dispatch system** that automates member transportation scheduling using geospatial clustering, real-world routing engines, and data-driven traffic simulation.

It allows users to:
- Upload structured Excel templates
- Validate and preprocess member and vehicle data
- Generate optimized directional groupings using wedge-based clustering
- Optimize routes using OSRM and Google OR-Tools
- Simulate inbound and outbound trip timings for each route
- Export structured schedules along with interactive visual route maps

The system combines geospatial clustering, constrained vehicle routing, and real-world road network optimization to generate efficient transportation schedules.

The system is designed for **fleet dispatch, shuttle coordination, and insurance-based transportation planning**.

---

<a name="tech-stack"></a>
## 🛠️ Tech Stack

- Python
- Tkinter (GUI)
- CustomTkinter (modern UI components)
- Pandas / NumPy (data processing)
- GeoPandas (geospatial processing)
- H3 (hexagonal spatial indexing)
- OSRM (Open Source Routing Machine)
- Google OR-Tools (CVRP optimization)
- OpenPyXL / xlwings (Excel automation)
- Folium (map visualization)

---

<a name="key-features"></a>
## ✨ Key Features

---

<a name="general"></a>
### General

- End-to-end desktop application built with Tkinter
- Full workflow: Excel upload → validation → optimization → export
- Automatic geospatial preprocessing and caching system

---

<a name="template-upload-system"></a>
### Template Upload System

- Upload structured Excel template file
- Each sheet represents a separate insurance group
- Validates required structure:
  - Depot information
  - Vehicle data
  - Member records
- Prevents processing of invalid templates

---

### Data Structure

#### 🏢 Depot
- Address
- Cached latitude / longitude (stored after first run)

#### 🚗 Vehicles
- Driver name
- Car plate
- Seat capacity

#### 👤 Members
- Member ID
- Name
- Date of birth
- Schedule (day-based routing)
- Address (geocoded and cached for reuse)

---

<a name="scheduling-inputs"></a>
### Scheduling Inputs

User selects:
- Service day
- Start time
- Insurance group

This defines:
- Which members are included in routing
- Start conditions for simulation
- Vehicle assignment scope

---

<a name="wedge-based-clustering"></a>
### Wedge-Based Clustering

Members are grouped into **directional spatial wedges around the depot**.

#### Concept
- The space around the depot is divided into angular fan-shaped slices
- Each slice is further split into:
  - Inner region (close to depot)
  - Outer region (farther away, subdivided for granularity)

#### Assignment Logic
- Inner members are located close to the depot
- Outer members are located farther from the depot and assigned to directional outer wedges
- Outer regions are typically more spatially sparse and cover longer travel distances

#### Routing Behavior

This structure directly influences routing efficiency:

- Outer members are served first as vehicles travel outward from the depot
- Inner members are picked up on the return path toward the depot
- Inner wedges act as consolidation zones for return trips

This ensures:
> Routes expand outward into sparse regions first, then naturally “collapse inward” toward dense pickup areas.

The result is:
- Reduced route overlap
- Better spatial continuity
- More efficient utilization of return trips

---

<a name="routing--optimization"></a>
### Routing & Optimization

#### Step 1: Distance Matrix (OSRM)
- Uses OSRM to compute real road-network distances and travel times
- Ensures routing reflects actual driving conditions

#### Step 2: Optimization (Google OR-Tools)
- Solves a Capacitated Vehicle Routing Problem (CVRP)
- Produces optimal pickup sequences per vehicle
- Enforces vehicle capacity constraints

---

<a name="traffic-aware-travel-time-simulation"></a>
### Traffic-Aware Travel Time Simulation

- Uses historical **NYC HVFHV trip data (TLC dataset)** combined with **NYC taxi zone geometries**
- Builds a data-driven model to estimate realistic travel times between zones
- Learns travel patterns based on:
  - Pickup zone
  - Dropoff zone
  - Time of day

This model is used to:
- Simulate traffic-aware travel times
- Adjust OSRM route durations using learned historical patterns
- Reduce reliance on static routing estimates

This creates a hybrid system where:
> OSRM provides road-network routing, while historical HVFHV data provides real-world traffic behavior corrections.

---

<a name="output-system"></a>
### Output System

The system generates:

#### 📊 Excel Output
- Vehicle assignments
- Route sequences
- Simulated pickup and dropoff timings (inbound & outbound)
- Wedge classifications
- Insurance-based grouping breakdown

#### 🗺️ Map Visualization
- Interactive route maps using Folium
- Filters by driver and trip number

---

<a name="system-architecture"></a>
## ⚙️ System Architecture

1. Upload Excel template
2. Validate structure
3. Geocode and cache addresses
4. Generate wedge-based spatial clusters
5. Assign vehicles to wedges
6. Build OSRM distance matrix
7. Apply traffic-aware time correction model
8. Run OR-Tools optimization
9. Export Excel + map visualization

---

<a name="challenges--lessons-learned"></a>
## ⚡ Challenges & Lessons Learned
