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

<!-- to build:
     % docker run --rm --volume $PWD/docs:/data --user $(id -u):$(id -g) --env JOURNAL=joss openjournals/inara
-->

# Summary

There exists a number of popular deep learning object detectors,
programs that will analyze an image and return the location of all
occurrences of objects from a known set of classes.  For time series
of images (e.g., video or sequences of stills), tracking objects over
time is important in order to classify or predict behaviors, to
estimate the abundances of object types, and a variety of other
tasks.  `yasmot` is a lightweight and flexible object tracker that can
process the output from popular object detectors and 
track objects over time from monoscopic or steroscopic camera
configurations, and also generate consensus detections from an ensemble
of object detectors.


# Statement of need

`yasmot` is a multi-object tracker, implemented in Python, and available
under a GPLv2 license.  In addition to tracking objects over time, it
can link observations between left and right cameras in a stereo
configuration, which further improves detection performance, and
allows extracting depth information and estimate the sizes of objects.

In contrast to more complex approaches, `yasmot` works with detections
only, linking observations across time based on position and
dimensions of object bounding boxes and on the classification outputs. 

...Fast, lightweight, etc few dependencies

Tracking: Gaussian.
Consensus classifications.

# Usage and options

<!-- installation? -->

## Controlling tracking sensitivity

The `--scale` parameter controls how the different bounding box pairs
are ranked when considered for tracking (or stereo matching).
The algorithm uses a Gaussian score for position and size, and this
parameter controls the sharpness (or temperature) of the Gaussian.
Generally, if you have large changes between frames (rapidly moving
objects or low frame rate, you can try reducing this parameter.

## Handling missing detections

Object detectors are sometimes unreliable, and objects may fail to be
detected, especially when they are partially occluded or otherwise
difficult to identify.  To remedy this, `yasmot` will attempt to link
tracks across missing detections.  The maximum gap allowed in a track
is controlled by the parameter `--max_age`.  The age is derived from
the frame name, and unless the frame name is a plain number, the
extraction can be specified with `--time_pattern`.

If desired, the missing observations can be inferred by specifying the
`--interpolate` option.  The interpolated detections can be identified
from their probability, which is set to 0.0000.

In case there are classes representing an unknown or unidentified
object, it is possible to specify the label with the `--unknown`
parameter to avoid having this class be called as a consensus class
for a track.

## Tracking stereo images

The `-s` option links objects taken with a stereoscopic camera setup.
Normally tracks will be generated, but the `--no-track` option can be
specified to only link detections between the cameras, and not in time.

## Ensemble predictions

If you run multiple object detectors, it may be useful to combine the
outputs into a consensus set of predictions.  This can be achieved
by specifying the `-c` option.  Again you can use `--no-track` if you
just want the frame-by-frame consensus and not perform tracking as
well.

## Using pixel-based coordinates

The YOLO object detector [@Redmon_2016_CVPR] outputs image coordinates as
fractional images, i.e. values in the range from 0 to 1.  Other object
detectors (/e.g./, RetinaNet [@lin2018focallossdenseobject]) instead outputs a CSV file
with pixel-based coordinates.  Since `yasmot` does not require
the images to be available, you therefore may need to specify the pixel size of
the images, e.g. as `--shape 1228,1027` when using pixel-based coordinates.

## Output formats

If the `-o` option is not specified, the output will be written to
`stdout`. If the option is specified as `-o outfile`, the
following files may result, depending on the selection of other
parameters specified:

 - `outfile.frames` - frame annotations in YOLO format, with track
   number added.  For stereo images, each line will contain the
   bounding boxes for both images.
 - `outfile.tracks` - the list of tracks with the sequence of
   observations that constitute each track.
 - `outfile.pred` - per track consensus class predictions.

# Examples

The following examples are taken from the included test suite and the
data files can be found in the `tests` directory.

## Perform tracking on a directory of predictions from YOLO:

    yasmot tests/lab2

## Perfom tracking with interpolation

    yasmot tests/lab2 --interpolate

## Perform tracking limiting gap size

Here, we only connect tracks with a maximum of two
frames without detections:

    yasmot --max_age 2 --time_pattern frame_\{:d\}.txt tests/lab2

## Perform tracking on stereo images 

The `-s` option allows the user to specify two input stream, here with
predictions in pixel-based CSV format.  Note that we must specify the
images size with `--shape`:

    yasmot -s --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv

## Only link stereo predictions without tracking

Again we use pixel-based RetinaNet predictions between the two cameras:

    yasmot -s --no-track --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv

## Merge predictions from multiple object detectors 

Here we use predictions from a familiy of YOLO v8 models to provide
ensemble predictions: 

    yasmot -c tests/consensus/y8x*


# Related work

<!-- from https://viso.ai/deep-learning/object-tracking/ -->
OpenCV: BOOSTING, MIL, KCF, CSRT, MedianFlow, TLD, MOSSE, and GOTURN
ByteTrack - integrated with Yolo
BoT-SORT - also in Yolo

Tracktor: The bells and whistles thing?
DeepSORT: Looks inside bboxes to match them  <!-- https://medium.com/analytics-vidhya/object-tracking-using-deepsort-in-tensorflow-2-ec013a2eeb4f -->

<!--
  # Acknowledgements

  We acknowledge contributions from Brigitta Sipocz, Syrtis Major, and Semyeong
  Oh, and support from Kathryn Johnston during the genesis of this project.
-->

# References

