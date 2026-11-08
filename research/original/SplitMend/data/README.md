# Dataset provenance and attribution

Software is MIT-licensed; these datasets remain under their own CC BY 4.0 licenses.
Original archive URLs, byte lengths and SHA256 values are in sources.json and clinical_sources.json. Downloads
are cached and checksum changes fail rather than silently replacing the study data.

* UCI Human Activity Recognition Using Smartphones: Jorge Reyes-Ortiz, Davide Anguita,
  Alessandro Ghio, Luca Oneto, Xavier Parra (2013), DOI 10.24432/C54S4K. All 10,299
  supplied feature vectors and subject labels are used. The official train/test division
  is preserved initially. Our row-random validation subset is a simulated workflow.
* Open University Learning Analytics Dataset: Jakub Kuzilek, Martin Hlosta, Zdenek
  Zdrahal (2017), DOI 10.6084/m9.figshare.5081998.v1; descriptive paper
  DOI 10.1038/sdata.2017.171. All 32,593 student-module-presentation rows from
  studentInfo.csv are used; they represent 28,785 distinct student IDs. We do not
  describe repeated course enrolments as 32,593 independent people.
* Beijing Multi-Site Air Quality: Song Chen (2017), DOI 10.24432/C5RK5G. The original
  420,768 hourly station rows yield 420,204 dependency windows after dropping the
  first 23 and last 24 timestamps at each of 12 stations. The temporal experiment
  audits dependency spans; it does not impute missing pollutants or train a forecaster.

* Diabetes 130-US Hospitals for Years 1999-2008: John Clore, Krzysztof Cios,
  Jon DeShazo, Beata Strack (2014), DOI 10.24432/C5230J. All 101,766 encounters
  from 71,518 distinct patient IDs are used, including three rows with gender
  Unknown/Invalid. Patient IDs define groups; encounter IDs identify observations.
  The released table does not contain hospital IDs or admission timestamps. We do
  not claim hospital-held-out or chronological evaluation. The public outcome,
  age and gender columns define 25 nonempty joint strata for the repair policy.
  Age bins and split construction are derived in scripts/clinical_data.py. This is
  a simulated evaluation workflow, not a clinical trial or patient-outcome study.

Transformations and constructed splits are implemented in scripts/datasets.py and
scripts/clinical_data.py. Derived
JSON manifests contain metadata, sample IDs and policies; feature values remain in the
original archives. No claims of defects in the datasets' official evaluation protocols
are made. CC BY 4.0: https://creativecommons.org/licenses/by/4.0/
