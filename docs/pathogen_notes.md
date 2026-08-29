# Pathogen Simulation Profiles: Literature Justifications

This document outlines the literature and quantitative microbial risk assessment (QMRA) assumptions used to paramaterize the pathogen profile schema.

## 1. Norovirus GII.4
- **Dose-Response**: Beta-Poisson ($lpha=0.111$, $eta=32.81$ usually, alternative $lpha=0.04$ per Teunis 2008). Used standard active_profiles base values.
- **Shedding**: High shedding in feces (up to $10^{11}$ copies/g), with the
  curve indexed by days since symptom onset and a 0.5-day presymptomatic
  window (Atmar et al., Emerg Infect Dis 2008).

## 2. SARS-CoV-2
- **Dose-Response**: Beta-Poisson ($lpha=0.18$, $eta=58.0$ based on Watanabe 2020 derived models for SARS-CoV-1 and adapted for CoV-2).
- **Shedding**: Peak viral load near symptom onset (days 4-6), with a
  2.0-day presymptomatic window (He et al., Nat Med 2020).

## 3. Influenza A
- **Dose-Response**: Exponential ($k=0.18$ based on Alford 1966 human challenge studies converted for aerosolized TCID50 limits; often modelled in QMRA between 0.012 - 0.18 depending on strain/route).
- **Shedding**: Upper respiratory shedding peaks shortly after symptom onset,
  with a 1.0-day presymptomatic window (Ip et al., Clin Infect Dis 2017).

## 4. Measles Virus
- **Dose-Response**: Exponential ($k=0.5$). Highly infectious via airborne route. Estimated very high probability of infection per inhaled quantum/particle.
- **Susceptibility**: Set very low ($0.08$) representing a highly vaccinated baseline population.

## 5. Legionella pneumophila
- **Dose-Response**: Exponential ($k=0.059$ based on Armstrong and Haas 2007).
- **Shedding**: No human-to-human shedding (set to 0.0). Environmental/waterborne acquisition only.
- **Illness**: Low clinical illness rate relative to infection probability ($\eta=0.05$).

## 6. Vibrio cholerae/parahaemolyticus
- **Dose-Response**: Beta-Poisson ($lpha=0.25$, $eta=16.2$ based on Hornick et al. / Haas QMRA models).
- **Shedding**: Massive shedding in rice water stool. Peak around $10^{11}$ copies.

## 7. Campylobacter jejuni
- **Dose-Response**: Beta-Poisson ($lpha=0.145$, $eta=7.59$ based on Black et al. 1988 human feeding studies / Medema 1996).
- **Shedding**: Protracted enteric shedding.

## 8. Clostridioides difficile
- **Dose-Response**: Exponential ($k=0.001$). Spore infection requires significant disruption of microflora; dose-response modeled with low probability per spore.
- **Deposition**: High surface deposition fraction ($0.05$) to reflect high environmental spore persistence.

## 9. Andes Hantavirus
- **Dose-Response**: Exponential ($k=0.01$). Rare human-to-human transmission modelled via hvac/droplet.
- **Shedding**: Aerosolized bodily fluids/excreta.

## 10. Ebola Virus
- **Dose-Response**: Exponential ($k=0.5$). Extremely low infectious dose via mucous membranes/contact.
- **Shedding**: Peaks late in disease course with very high viral loads in bodily fluids. No asymptomatic shedding modelled.

## Limitations
- Shedding curves are simplified to 15-day discrete arrays representing
  $\log_{10}$ daily shedding indexed from symptom onset; absent a profile
  window, hosts do not shed before onset.
- Disruption magnitudes and taxa fold-changes are illustrative directional shifts based on expected microbiome derangements, not precise longitudinal kinetic data.
