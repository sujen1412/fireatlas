""" FireObj
This is the module defining fire objects used for fire tracking

FOUR LAYERS OF OBJECTS
    a. Allfires:  the class of all fire events
    b. Fire:      the class of a fire event
    c. Cluster:   the class of active fire pixel cluster (only for supporting)
    d. FirePixel: the class of an active fire pixel
"""
from utils import timed
from FireLog import logger

# a. Object - Allfires
class Allfires:
    """ Class of allfire events at a particular time step
    """

    # initilization
    def __init__(self, t):
        """ Initiate the object with current time
        Parameters
        ----------
        t : tuple, (int,int,int,str)
            the year, month, day and 'AM'|'PM'
        """
        # self.t = FireTime.t_nb(t,nb='previous') # initialize the object at the previous time step
        self.t = t

        # Allfires object contains a dict of Fire objects with fireID as the key (will be added after reading active fire data)
        self.fires = {}

        # Initiate lists storing fire ids which will changes at the current time step
        self.fids_expanded = (
            []
        )  # a list of ids for fires with expansion at current time step
        self.fids_new = (
            []
        )  # a list of ids for all new fires formed at current time step
        self.fids_merged = (
            []
        )  # a list of ids for fires with merging at current time step
        self.fids_invalid = (
            []
        )  # a list of ids for fires invalidated at current time step

        # cumulative recordings
        self.heritages = []  # a list of fire heritage relationships (source, target)
        self.id_dict = (
            []
        )  # this list relates the list position of the fire in the allfires object to the fire id
        # (list_index, fireid) (list position can be variable when writing out only active fires)

    def __repr__(self):
        return f"<Allfires at t={self.t} with n_fires={len(self.fires)}>"
    
    # properties
    @property
    def cday(self):
        """ Datetime date of current time step
        """
        from datetime import date

        return date(*self.t[:-1])

    @property
    def ampm(self):
        """ Ampm indicator of current time step
        Parameters
        ----------
        ampm : str, 'AM'|'PM'
           the ampm option calculated from t
        """
        return self.t[-1]

    @property
    def fids(self):
        """ List of fire ids
        """
        return [i for i, f in self.fires.items()]

    @property
    def number_of_fires(self):
        """ Total number of fires (active and inactive) at this time step
        """
        return len(self.fires)

    @property
    def fids_active(self):
        """ List of active fire ids
        """
        return [i for i, f in self.fires.items() if f.isactive]

    @property
    def number_of_activefires(self):
        """ Total number of active fires at this time step
        """
        return len(self.fids_active)

    @property
    def activefires(self):
        """ dict of active fires
        """
        return {i: f for i, f in self.fires.items() if f.isactive}

    @property
    def mayactivefires(self):
        """ dict of active fires and sleepers
        """
        return {i: f for i, f in self.fires.items() if (f.isactive or f.mayreactivate)}

    @property
    def deadfires(self):
        """ dict of inactive fires not going to be reactivated
        """
        return {
            i: f for i, f in self.fires.items() if not (f.isactive or f.mayreactivate)
        }

    @property
    def fids_dead(self):
        """ List of fire ids that is not going to be reactivated
        """
        return [i for i, f in self.fires.items() if not (f.isactive or f.mayreactivate)]

    @property
    def fids_sleeper(self):
        """ List of fire ids that may reactivate
        """
        return [i for i, f in self.fires.items() if f.mayreactivate]

    @property
    def number_of_sleeper(self):
        """ Total number of sleep fires at this time step
        """
        return len(self.fids_sleeper)

    @property
    def fids_valid(self):
        """ List of valid (non-invalid) fire ids
        """
        # return [self.fires[f].fireID for f in self.fires if self.fires[f].invalid is False]
        return [i for i, f in self.fires.items() if f.invalid is False]

    @property
    def number_of_validfires(self):
        """ Total number of valid fires at this time step
        """
        return len(self.fids_valid)

    @property
    def validfires(self):
        """ List of valid fires
        """
        # return [self.fires[fid] for fid in self.fids_valid]
        return {i: f for i, f in self.fires.items() if f.invalid is False}

    @property
    def fids_updated(self):
        """ List of fire id which is updated at this time step
            (expanded, new, merged, invalid)
        """
        fids_updated = list(
            set(
                self.fids_expanded
                + self.fids_new
                + self.fids_merged
                + self.fids_invalid
            )
        )
        return fids_updated

    @property
    def fids_ne(self):
        """ List of fire id which is newly formed or expanded
               at this time step
        """
        fids_ne = sorted(set(self.fids_expanded + self.fids_new))
        return fids_ne

    # functions to be run before tracking VIIRS active fire pixels at each time step
    def update_t(self, t):
        """ Update the time (cday and ampm) for the Allfire object.
        Parameters
        ----------
        t : tuple, (int,int,int,str)
            the year, month, day and 'AM'|'PM'
        """
        self.t = list(t)  # current date and ampm

    def update_t_allfires(self, t):
        """ Update the time (t) for each Fire object in the Allfire object.
        Parameters
        ----------
        t : tuple, (int,int,int,str)
            the year, month, day and 'AM'|'PM'
        """
        for i, f in self.fires.items():
            f.t = list(t)

    def cleanup(self, t):
        """ Clean up Allfires obj at each time step
        - update t (for allfires and all fires)
        - clean up lists to record fire changes
        - clean up newpixels for each fire
        """
        # time updated to t
        self.update_t(t)  # update t for allfires
        self.update_t_allfires(t)  # update t

        # reset the fids used to record changes
        self.fids_expanded = (
            []
        )  # a list of ids for fires with expansion at current time step
        self.fids_new = (
            []
        )  # a list of ids for all new fires formed at current time step
        self.fids_merged = (
            []
        )  # a list of ids for fires with merging at current time step
        self.fids_invalid = (
            []
        )  # a list of ids for fires invalidated at current time step

    def newyear_reset(self, regnm):
        """ reset fire ids at the start of a new year
        """
        import FireIO

        # re-id all active fires
        newfires = {}
        fidmapping = []
        fids_keep = self.fids_active + self.fids_sleeper
        for i, fid in enumerate(fids_keep):
            newfires[i] = self.fires[fid]  # record new fireID and fire object
            newfires[i].fireID = i  # also update fireID attribute of fire object
            fidmapping.append((fid, i))
        self.fires = newfires

        # lastyearfires = {}
        # fidmapping = []
        # nfid = 0
        # for f in self.activefires:
        #     ofid = f.fireID
        #     f.fireID = nfid
        #     # lastyearfires.append(f)
        #     lastyearfires[nfid] = f
        #     fidmapping.append((ofid,nfid))
        #     nfid += 1
        # self.fires = lastyearfires

        # clean heritages
        self.heritages = []

        # save the mapping table
        if len(fidmapping) > 0:
            FireIO.save_newyearfidmapping(fidmapping, self.t[0], regnm)

    # functions to be run after tracking VIIRS active fire pixels at each time step
    def record_fids_change(
        self, fids_expanded=None, fids_new=None, fids_merged=None, fids_invalid=None
    ):
        """ Update the list of ids for fires with changes at current time step.
        Parameters
        ----------
        fids_expanded : list
            ids of expanded fires
        fids_new : list
            ids of new formed fires
        fids_merged : list
            ids of fires with other fires merging to them
        fids_invalid : list
            ids of fires invalidated (due to merging with other fires)
        """
        if fids_expanded:
            self.fids_expanded = fids_expanded  # expanded fires
        if fids_new:
            self.fids_new = fids_new  # new formed fires
        if fids_merged:
            self.fids_merged = fids_merged  # fires with merging with other fires
        if fids_invalid:
            self.fids_invalid = (
                fids_invalid  # fires invalidated due to merging with other fires
            )

    @timed
    def invalidate_statfires(self):
        """ If pixel density of an active fire is too large, assume it's static
                fires and invalidate it.
        """
        for f in self.activefires.values():
            if (f.pixden > 20) & (f.farea < 20):
                # invalidate the fire
                f.invalid = True

                # add the fire id into the fids_invalid list
                self.fids_invalid.append(f.fireID)

# b. Object - Fire
class Fire:
    """ Class of a single fire event at a particular time step
    """

    def __init__(self, id, t, pixels, allpixels, sensor="viirs"):
        """ Initialize Fire class with active fire pixels locations and t. This
            is only called when fire clusters forming a new Fire object.
        Parameters
        ----------
        id : int
            fire id
        t : tuple, (int,int,int,str)
            the year, month, day and 'AM'|'PM'
        pixels : list (nx5)
            latitude, longitude, line, sample, and FRP values of active fire pixels
        allpixels : dataframe
            all fire pixels for the period of interest
        sensor : str
            the remote sensing instrument, 'viirs' | 'modis'; no differentiation
            between SNPP and NOAA20
        """
        from FireConsts import FTYP_opt
        import FireVector, FireTime, FireIO

        # initialize fire id and sensor
        self._fid = id
        self.mergeid = id  # mergeid is the final fire id the current fire being merged; use current fire id at initialization
        self.sensor = sensor
        self.allpixels = allpixels

        # initialize current time, fire start time, and fire final time
        tlist = list(t)  # convert (y,m,d,ampm) to [y,m,d,ampm]
        self.t = tlist  # current time
        self.t_st = tlist
        self.t_ed = tlist

        self.pixels = pixels

        # initialize hull using the pixels
        hull = FireVector.cal_hull(pixels[["x", "y"]].values, sensor)  # the hull from all locs
        self.hull = hull  # note fire.hull is not automatically updated (need explicit calculation if changes occur)

        # fline of latest active timestep, used for sleeper threshold
        self.fline_prior = None

        # always set valid at initialization
        self.invalid = False

        if FTYP_opt == 1:
            # TODO: get and record fm1000 value at ignition
            # lon, lat = self.ignition_center_geo
            # self.stFM1000 = FireIO.get_stFM1000(FireTime.t2d(t), lon=lon, lat=lat)
            self.stFM1000 = 0

    @property
    def cday(self):
        """ Current day (datetime date)
        """
        from datetime import date

        return date(*self.t[:-1])

    @property
    def cdoy(self):
        """ Current day (datetime date)
        """
        return self.cday.timetuple().tm_yday

    @property
    def ampm(self):
        """ Current ampm flag, 'AM'|'PM'
        """
        return self.t[-1]

    @property
    def duration(self):
        """ Time difference between first and last active fire detection
        """
        import FireTime

        duration = FireTime.t_dif(self.t_st, self.t_ed)  # + 0.5
        return duration

    @property
    def t_inactive(self):
        """ Time difference between current time and the last active fire detection
        """
        import FireTime

        t_inactive = FireTime.t_dif(self.t_ed, self.t)
        return t_inactive

    @property
    def isactive(self):
        """ Fire active status
        """
        from FireConsts import maxoffdays

        # invalidated fires are always inactive
        if self.invalid:
            return False
        # otherwise, set to True if no new pixels detected for 5 consecutive days
        return self.t_inactive <= maxoffdays

    @property
    def isdead(self):
        """ Fire active status
        """
        from FireConsts import limoffdays

        # invalidated fires are always inactive
        if self.invalid:
            return True
        # otherwise, set to True if no new pixels detected for 5 consecutive days
        return self.t_inactive > limoffdays

    @property
    def mayreactivate(self):
        """ Fire sleeper status
        """
        from FireConsts import maxoffdays, limoffdays

        # invalidated fires are always inactive
        if self.invalid:
            return False
        # otherwise, set to True if no new pixels detected for 5 consecutive days
        return maxoffdays < self.t_inactive <= limoffdays

    @property
    def isignition(self):
        """ Is the current timestep the ignition?
        when start time == end time; and new pixel > 0
        """
        return self.t == self.t_st
    
    @property
    def fireID(self):
        return self._fid

    @property
    def pixels(self):
        return self.allpixels[self.allpixels["fid"] == self.fireID]

    @pixels.setter
    def pixels(self, pixels):
        self.allpixels.loc[pixels.index, "fid"] = self.fireID

    @property
    def locs(self):
        """ List of fire pixel locations (x, y)
        """
        return self.pixels[["x", "y"]].values

    @property
    def locs_geo(self):
        """ List of fire pixel locations (lat,lon)
        """
        return self.pixels[["Lon", "Lat"]].values

    @property
    def locsMP(self):
        """ MultiPoint shape of locs
        """
        from shapely.geometry import MultiPoint

        mp = MultiPoint(self.locs)
        return mp

    @property
    def n_pixels(self):
        """ Total number of fire pixels"""
        return len(self.pixels)
    
    @property
    def newpixels(self):
        import FireTime
        return self.pixels[self.pixels["t"] == FireTime.t2dt(self.t)]

    @property
    def newlocs(self):
        """ List of new fire pixels locations (lat,lon)
        """
        return self.newpixels[["x", "y"]].values

    @property
    def newlocs_geo(self):
        """ List of new fire pixels locations (lat,lon)
        """
        return self.newpixels[["Lon", "Lat"]].values

    @property
    def newlocsMP(self):
        """ MultiPoint shape of newlocs
        """
        from shapely.geometry import MultiPoint

        mp = MultiPoint(self.newlocs)
        return mp


    @property
    def newpixelatts(self):
        """ List of new fire pixels attributes
        """
        return [
            (p.Lon, p.Lat, p.FRP, p.DS, p.DT, p.YYYYMMDD_HHMM, p.ampm, p.Sat)
            for p in self.newpixels
        ]

          
    @property
    def newpixelatts(self):
        """ List of new fire pixels attributes
        """
        return [
            (p.Lon, p.Lat, p.FRP, p.DS, p.DT, p.YYYYMMDD_HHMM, p.ampm, p.Sat)
            for p in self.newpixels
        ]

    @property
    def n_newpixels(self):
        """ Total number of new fire pixels
        """
        return len(self.newpixels)
    
    @property
    def ignpixels(self):
        import FireTime
        return self.pixels[self.pixels["t"] == FireTime.t2dt(self.t_st)]
    
    @property
    def ignition_center_geo(self):
        from shapely.geometry import MultiPoint

        ignMP = MultiPoint(self.ignpixels[["Lon", "Lat"]].values)

        ignition_centroid = ignMP.centroid
        return (ignition_centroid.x, ignition_centroid.y)

    @property
    def farea(self):
        """ Fire spatial size of the fire event (km2)
        """
        from FireConsts import area_VI

        # get hull
        fhull = self.hull

        # If no hull, return area calculated from number of pixels
        if fhull is None:
            return self.n_pixels * area_VI
        else:
            area_cal = fhull.area / 1e6
            return max(area_cal, area_VI)

    @property
    def pixden(self):
        """ Fire pixel density (number of pixels per km2 fire area)
        """
        farea = self.farea
        if farea > 0:
            return self.n_pixels / farea
        else:
            return 0

    @property
    def ftypename(self):
        """ Fire type name
        """
        import FireFuncs

        return FireFuncs.set_ftypename(self)

    @property
    def fperim(self):
        """ Perimeter length of fire hull
        """
        fhull = self.hull

        if fhull is None:
            perim = 0
        else:
            perim = fhull.length / 1e3  # km
        return perim

    @property
    def flinepixels(self):
        """ List of all fire pixels near the fire perimeter (fine line pixels)
        """
        import FireVector
        
        if self.hull is None:
            return []
        try:
            indices = FireVector.get_fline_pixels(self.newpixels, self.hull)
            return self.newpixels[indices]
        except Exception as e:
            print(e)
            return []

    @property
    def flplocs(self):
        """ List of fire line pixel locations (lat,lon)
        """
        return self.flinepixels[["x", "y"]].values

    @property
    def n_flinepixels(self):
        """ Total number of fire line pixels
        """
        return len(self.flinepixels)
    
    @property
    def meanFRP(self):
        """Mean FRP of the new fire pixels
        """
        return self.newpixels.FRP.mean()

    @property
    def fline(self):
        """ Active fire line MultiLineString shape (segment of fire perimeter with active fires nearby)
        """
        from shapely.geometry import MultiLineString, MultiPoint
        from FireConsts import flbuffer, VIIRSbuf

        # this happens if last active pixels are within the fire scar
        if self.n_flinepixels == 0:
            return None

        flinelocsMP = MultiPoint(self.flplocs).buffer(VIIRSbuf)

        # get the hull
        fhull = self.hull

        # calculate the fire line
        if fhull is None:  # if no hull, return None
            return None
        else:  # otherwise, create shape of the active fire line
            if fhull.type == "MultiPolygon":
                # extract exterior of fire perimeter
                mls = MultiLineString([plg.exterior for plg in fhull.geoms])
                # set fline to the part which intersects with  bufferred flinelocsMP
                fline = mls.intersection(flinelocsMP.buffer(flbuffer))

            elif fhull.type == "Polygon":
                mls = fhull.exterior
                fline = mls.intersection(flinelocsMP.buffer(flbuffer))
            else:  # if fhull type is not 'MultiPolygon' or 'Polygon', return flinelocsMP
                fline = flinelocsMP

            # we save the fire line to a new property (this is only updated when fline not None)
            self.fline_prior = fline

            return fline

    @property
    def flinelen(self):
        """ The length of active fire line
        """
        try:
            flinelen = self.fline.length / 1e3  # km
        except:
            flinelen = 0

        return flinelen

    # functions
    def updateftype(self):
        """ Update fire type
        # do not use ftype as property since it may mess up when t updates (without pixel addition)
        """
        import FireFuncs

        self.ftype = FireFuncs.set_ftype(self)

    def updatefhull(self, newlocs):
        """ Update the hull using old hull and new locs
        """
        import FireVector

        hull = FireVector.cal_hull(newlocs, sensor=self.sensor)
        # use the union to include hull in past time step
        phull = self.hull
        self.hull = phull.union(hull)
