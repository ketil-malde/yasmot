---
title: 'YASMOT: Yet another stereo image multi-object tracker'
tags:
  - Python
  - object detection
  - tracking
  - stereo images
authors:
  - name: Ketil Malde
    orcid: 0000-0000-0000-0000
    affiliation: "1, 2" # (Multiple affiliations must be quoted)
affiliations:
 - name: Insitute of Marine Research, Bergen, Norway
   index: 1
 - name: Department of Informatics, University of Bergen, Norway
   index: 2
date: 2024-01-
bibliography: paper.bib
---

# Summary

There exists a number of popular deep learning object detectors,
programs that will take an image and return the location of all
occurrences of objects from a known set of classes.  For time series
of images (e.g., video or sequences of stills), it is often useful to
track objects over time.

# Statement of need

YASMOT is a multi-object tracker, implemented in Python, and available
under a GPLv2 license.  In addition to tracking objects over time, it
can link observations between left and right cameras in a stereo
configuration, which further improves detection performance, and
allows extracting depth information and estimate the sizes of objects.

In contrast to more complex approaches, `yasmot` works with detections
only, linking observations across time based on position and
dimensions of object bounding boxes and on the classification outputs. 

# Output formats


# Algorithm

# Usage examples

# Related work

<!-- from https://viso.ai/deep-learning/object-tracking/ -->
OpenCV: BOOSTING, MIL, KCF, CSRT, MedianFlow, TLD, MOSSE, and GOTURN
ByteTrack - integrated with Yolo
BoT-SORT - also in Yolo

Tracktor: The bells and whistles thing?
DeepSORT: Looks inside bboxes to match them  <!-- https://medium.com/analytics-vidhya/object-tracking-using-deepsort-in-tensorflow-2-ec013a2eeb4f -->

# Citations

Citations to entries in paper.bib should be in
[rMarkdown](http://rmarkdown.rstudio.com/authoring_bibliographies_and_citations.html)
format.

If you want to cite a software repository URL (e.g. something on GitHub without a preferred
citation) then you can do it with the example BibTeX entry below for @fidgit.

For a quick reference, the following citation commands can be used:
- `@author:2001`  ->  "Author et al. (2001)"
- `[@author:2001]` -> "(Author et al., 2001)"
- `[@author1:2001; @author2:2001]` -> "(Author1 et al., 2001; Author2 et al., 2002)"

# Figures

Figures can be included like this:
![Caption for example figure.\label{fig:example}](figure.png)
and referenced from text using \autoref{fig:example}.

Figure sizes can be customized by adding an optional second parameter:
![Caption for example figure.](figure.png){ width=20% }

# Acknowledgements

We acknowledge contributions from Brigitta Sipocz, Syrtis Major, and Semyeong
Oh, and support from Kathryn Johnston during the genesis of this project.

# References
