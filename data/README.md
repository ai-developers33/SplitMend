# Dataset provenance and attribution

Software is MIT-licensed; these datasets remain under their own CC BY 4.0 licenses.
Original archive URLs, byte lengths and SHA256 values are in sources.json. Downloads
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

Transformations and constructed splits are implemented in scripts/datasets.py. Derived
JSON manifests contain metadata, sample IDs and policies; feature values remain in the
original archives. No claims of defects in the datasets' official evaluation protocols
are made. CC BY 4.0: https://creativecommons.org/licenses/by/4.0/
