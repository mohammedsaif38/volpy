import pandas as pd
import os
from xml.dom.minidom import parse
from coordinates import CoordinateSystem
from coordinates import UtmCoordinate


class Survey():
    """
    The survey class is the starting point of this library
    Its data source is expected to represent a collection of points within a
    cartesian coordinate system.
    """

    def __init__(
        self,
        source,
        name,
        coordinate_system=CoordinateSystem.CARTESIAN):
        """Initializes a survey object

        Arguments:
        source: path to the file that contains the survey data.
                     Accepted file types: .xlsx, .xls, .csv, .gpx
        name: a meaningful name for this survey (str)
        coordinate_system: an enumeration based on available coordinate systems
                           at the coordinates module
        """

        # Validate if extension is supported.
        (_, extension) = os.path.splitext(source)
        accepted_extensions = set(['.xlsx','.xls','.gpx','.csv', '.txt'])
        extension = extension.lower()
        if extension not in accepted_extensions:
            raise TypeError(
                "The file extension provided is not currently supported.")

        # initialize class
        self.name = name
        self.source = source
        self.coordinate_system = coordinate_system
        
        if extension == '.gpx':
            self.data = self._read_gpx()
        elif (extension == '.csv') or (extension == '.txt'):
            self.data = self._read_csv()
        elif (extension == '.xlsx') or (extension == '.xls'): # MS Excel
            self.data = self._read_excel()
        else:
            raise ValueError("Error while parsing supported file extension.")

    def _read_gpx(self):
        """Parses an xml file containing GPS data
        Data points are assumed to be in a Geographic coordinate system

        Returns a pandas DataFrame containing the parsed GPS data if parse was
        successful and None otherwise.
        """

        # Parsing XML file
        collection = parse(self.source).documentElement
        track_points = collection.getElementsByTagName("trkpt")
        if len(track_points) == 0:
            raise ValueError("Unexpected trackpoint tag on XML file")
        points = []

        for point in track_points:
            # Parse from XML
            latitude = point.getAttribute("lat")
            longitude = point.getAttribute("lon")
            elevation = point.getElementsByTagName('ele')[0]\
                .childNodes[0].data

            if (not latitude or
                not longitude or
                not elevation):
                raise ValueError("Unexpected tag for lat/lon/ele.")

            try:
                latitude = pd.to_numeric(latitude)
                longitude = pd.to_numeric(longitude)
                elevation = pd.to_numeric(elevation)
                utm = UtmCoordinate.create_from_geographic(
                    latitude,
                    longitude,
                    elevation)
                entry = (latitude,
                        longitude,
                        utm.elevation,
                        utm.northing,
                        utm.easting)
                points.append(entry)
            except Exception as exception:
                raise exception

        # Generate DataFrame
        columns = ['latitude',
                   'longitude',
                   'elevation',
                   'northing',
                   'easting']
        data = pd.DataFrame.from_records(points,
                                         columns=columns)

        # Generate x, y, z
        data['x'] = data['easting'] - data['easting'].min()
        data['y'] = data['northing'] - data['northing'].min()
        data['z'] = data['elevation'] - data['elevation'].min()
        selection = ['x', 'y', 'z', 'elevation']
        return data[selection]
                                         
    def _read_csv(self):

        if self.coordinate_system == CoordinateSystem.GEOGRAPHIC:
            try:
                data = pd.read_csv(self.source)
                
                if data.shape[1] != 3:
                    raise ValueError("Unexpected number of columns")

                # Verify expected column names
                expected_columns = ['latitude', 'longitude', 'elevation']
                for item in data.columns:
                    if item not in expected_columns:
                        raise ValueError("Unexpected column name. Expected:{}"\
                        .format(expected_columns))

                # Convertion to numeric:
                for column in data.columns:
                    data[column] = pd.to_numeric(data[column])
                
                # Generate UTM and then Cartesian
                def generate_utm(row):
                    return UtmCoordinate.create_from_geographic(
                        row['latitude'],
                        row['longitude'],
                        row['elevation'])
                data['UTM'] = data.apply(generate_utm, axis=1)
                data['easting'] = data.apply(lambda row: row['UTM'].easting,
                                             axis=1)
                data['northing'] = data.apply(lambda row: row['UTM'].northing,
                                              axis=1)
                data['x'] = data['easting'] - data['easting'].min()
                data['y'] = data['northing'] - data['northing'].min()
                data['z'] = data['elevation'] - data['elevation'].min()
                selection = ['x', 'y', 'z', 'elevation']
                return data[selection]

            except Exception as exception:
                print(exception)
                raise exception

        if self.coordinate_system == CoordinateSystem.CARTESIAN:
            pass

        if self.coordinate_system == CoordinateSystem.UTM:
            pass

    def _read_excel(self):
        return True
