from collections import namedtuple

BBox = namedtuple('BBox', 'frameid x y w h cls pr')  # :: Doubles

Frame = namedtuple('Frame', 'frameid bboxes') # :: [BBox]

BBpair = namedtuple('BBPair', 'bbleft bbright')

Track = namedtuple('Track', 'bbpairs')

