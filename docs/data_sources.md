# Data Sources — BRAHMO Rules Engine

## Overview

All clinical data used in this assessment is **synthetic** — created specifically for the Supra Multi-Specialty Hospital demo scenario. No real patient data, real hospital data, or real clinical trial data is used.

## Source Categories

### 1. Drug Safety Constraints (10 Zone 2 GLOBAL nodes)

| Node | Medical Basis | Source Type |
|------|--------------|-------------|
| N-G01: Warfarin-NSAID Interaction | Well-established pharmacological contraindication. FDA Black Box Warning for NSAIDs in anticoagulated patients. | Clinical pharmacology reference (UpToDate, BNF) |
| N-G02: Penicillin Allergy Cross-Reactivity | Published cross-reactivity rates: ~10% for 1st-gen cephalosporins, <2% for 3rd-gen (Campagna et al., 2012) | Clinical immunology literature |
| N-G03: Blood Transfusion Verification | Standard blood bank protocol (WHO Blood Transfusion Safety guidelines) | WHO clinical guidelines |
| N-G04: Hand Hygiene Compliance | WHO "5 Moments for Hand Hygiene" campaign | WHO patient safety guidelines |
| N-G05: Verbal Orders | Joint Commission International (JCI) standard for medication safety | Hospital accreditation standards |
| N-G06: Patient Identification | Joint Commission National Patient Safety Goals | Hospital safety protocols |
| N-G07: Emergency Codes | Standardized hospital emergency code system | Hospital administration reference |
| N-G08: Antibiotic Stewardship | WHO Global Action Plan on Antimicrobial Resistance, 72-hour review rule | WHO antimicrobial guidelines |
| N-G09: Fall Risk Assessment | Morse Fall Scale (Morse et al., 1989), standard admission assessment | Published clinical tool |
| N-G10: Formulary Brands | Fictional brand preferences for Supra Hospital | Synthetic organizational data |

### 2. Orthopaedic Protocols (15 nodes)

| Node | Medical Basis | Source Type |
|------|--------------|-------------|
| N-O01: Post-Op Vitals | Standard post-operative monitoring protocol | Clinical practice guidelines |
| N-O02: Paracetamol Post-TKR | WHO analgesic ladder, multimodal analgesia for joint replacement | Orthopedic pain management protocols |
| N-O03: 48-Hour Discharge Rule | Enhanced Recovery After Surgery (ERAS) protocols for TKR | ERAS Society guidelines |
| N-O04: Zimmer Implants | Fictional vendor preference for Supra Hospital | Synthetic organizational data |
| N-O06: DVT Prophylaxis | AAOS/ACC guidelines for VTE prophylaxis after joint replacement | American Academy of Orthopaedic Surgeons |
| N-O07: Fracture X-Ray | Standard radiographic protocol for fracture assessment | Emergency medicine guidelines |
| N-O09: Post-TKR Physio | Early mobilization protocol within 24 hours | ERAS physiotherapy guidelines |
| N-O10: Weight-Bearing | Standard fracture management protocol | Orthopedic textbooks |
| N-O11, N-O12: Budget/Vendor | Fictional administrative data for Supra Hospital | Synthetic organizational data |
| N-O13, N-O14: Patient Rajan | Fictional patient case — based on common Warfarin + ortho surgery scenarios | Synthetic patient data |
| N-O15: Handover Protocol | SBAR (Situation-Background-Assessment-Recommendation) framework | Joint Commission communication standard |

### 3. Medicine Protocols (8 nodes)

| Node | Medical Basis | Source Type |
|------|--------------|-------------|
| N-M01: Diabetic Fasting | Ramadan fasting guidelines for diabetic patients (IDF/DAR guidelines) | International Diabetes Federation |
| N-M02: Sepsis Protocol v3 | Surviving Sepsis Campaign 2021 guidelines (1-hour bundle) | SCCM/ESICM guidelines |
| N-M03: Insulin Sliding Scale | Standard endocrinology practice — basal-bolus over sliding scale | Diabetes management guidelines |
| N-M04: Patient Padma | Fictional patient — based on common Type 2 DM + religious fasting patterns | Synthetic patient data |
| N-M06: Contrast Allergy | Standard premedication protocol for contrast allergy (Prednisone/Diphenhydramine) | ACR Manual on Contrast Media |
| N-M08: Sepsis v2 (SUPERSEDED) | Previous iteration of sepsis protocol, now replaced by v3 | Historical guideline reference |

### 4. Cardiology Protocols (5 nodes)

| Node | Medical Basis | Source Type |
|------|--------------|-------------|
| N-C01: Catheterization Consent | Standard informed consent for invasive cardiac procedures | Cardiology practice standards |
| N-C02: Troponin Protocol | High-sensitivity troponin rule-out algorithm (ESC 2020 guidelines) | European Society of Cardiology |
| N-C03: ECHO After MI | Standard post-MI workup — echocardiography before discharge | ACC/AHA guidelines |
| N-C04: ATOM-2026 Trial | Fictional research trial | Synthetic clinical trial data |
| N-C05: DAPT Duration | Standard dual antiplatelet therapy duration post-DES (ESC 2020) | European Society of Cardiology |

### 5. Paediatric Protocols (3 nodes)

| Node | Medical Basis | Source Type |
|------|--------------|-------------|
| N-P01: Weight-Based Dosing | Standard paediatric pharmacology — all doses mg/kg | BNF for Children |
| N-P02: Visiting Hours | Family-centered care approach in paediatrics | Hospital policy reference |
| N-P03: Penicillin Allergy | Fictional patient case — paediatric penicillin allergy | Synthetic patient data |

### 6. Administrative Nodes (4 nodes)

| Node | Source Type |
|------|------------|
| N-A01: Expansion Plan | Synthetic organizational data |
| N-A02: Salary Restructuring | Synthetic organizational data |
| N-A03: Accreditation Status | Based on NABH (National Accreditation Board for Hospitals) standards |
| N-A04: Legal Hold | Synthetic medico-legal scenario |

### 7. High-Derivability Nodes (5 nodes)

These contain general medical knowledge that an AI already knows from training:
| Node | Why Derivable |
|------|--------------|
| N-D01: What is TKR | Standard medical textbook definition |
| N-D02: Paracetamol Mechanism | Basic pharmacology |
| N-D03: Normal Vital Signs | Standard clinical reference |
| N-D04: What is DVT | Standard medical textbook definition |
| N-D05: What is Type 2 DM | Standard medical textbook definition |

## DAG Hierarchy Structure

The 15-level hierarchy is modeled after a typical Indian multi-specialty hospital organizational structure:

```
L1  Hospital Root
L3  Divisions (Clinical, Administrative)
L5  Departments (Ortho, Medicine, Cardiology, Paeds, Surgery, ICU)
L8  Sub-departments (Ortho General, TKR Unit, CCU)
L10 Wards (Ortho Ward, Medicine Ward, Paeds Ward)
L12 Patient-level (individual patient constraints)
```

## User Profiles

7 user profiles based on typical hospital staff roles:
| User | Role | Based On |
|------|------|----------|
| Nurse Priya | VIEWER | Staff nurse on night shift |
| Dr. Vikram | HOD | Head of Orthopaedics |
| Dr. Ananya | EDITOR | Medicine registrar |
| Dr. Sharma | HOD | Head of Medicine |
| Pharmacist Ravi | VIEWER | Hospital pharmacist |
| Dr. Sunita | QUALITY | Quality assurance officer |
| Admin Suresh | ADMIN | Hospital administrator |

## Compliance Tags

- **MNPI** (Material Non-Public Information): Budget data, vendor negotiations, research trial data
- **PHI** (Protected Health Information): Patient-identifiable data
- **CONFIDENTIAL**: Internal administrative decisions

## Disclaimer

All data is synthetic and for demonstration purposes only. No real patient data, real hospital data, or proprietary clinical information is used. The medical knowledge referenced (drug interactions, clinical protocols, etc.) is based on publicly available clinical guidelines and textbooks.