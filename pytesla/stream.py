import urllib.request
import base64

#import http.client
#http.client.HTTPConnection.debuglevel = 1

class StreamEvents:
    SPEED            = 'speed'         # int, or str if shift_state is ''
    ODOMETER         = 'odometer'      # float
    STATE_OF_CHARGE  = 'soc'           # int
    ELEVATION        = 'elevation'     # int
    HEADING          = 'est_heading'   # int
    LATITUDE         = 'est_lat'       # float
    LONGITUDE        = 'est_lng'       # float
    POWER            = 'power'         # int
    SHIFT_STATE      = 'shift_state'   # str
    ALL              = ['speed', 'odometer', 'soc', 'elevation',
                        'est_heading', 'est_lat', 'est_lng', 'power',
                        'shift_state']

class Stream:
    def __init__(self, vehicle):
        self._vehicle = vehicle
        self._request = None
        self._log = vehicle._log

    def __repr__(self):
        return "<Stream {}>".format(str(self._vehicle))

    def connect(self, events):
        self._log.debug("Stream connect")
        n = 0

        while (n < 2):
            n += 1

            self._log.debug("Stream connect iteration {}".format(n))

            token = self._vehicle.stream_auth_token
            auth_str = "{}:{}".format(self._vehicle.email, token)
            auth = base64.b64encode(bytes(auth_str, 'utf-8')).decode('utf-8')
            params = "?values=" + ','.join(events)

            url ='https://streaming.vn.teslamotors.com/stream/{}/{}' \
                .format(self._vehicle.vehicle_id, params)
            headers = {'Authorization': 'Basic {}'.format(auth)}

            self._request = urllib.request.Request(url, headers = headers)

            try:
                response = urllib.request.urlopen(self._request)
            except urllib.error.HTTPError as e:
                if e.code == 401 and e.reason == "provide valid authentication":
                    self._log.debug("Authentication error, retrying")
                    self._vehicle.refresh()

                    continue

                raise e

            self._log.debug("Stream connection established")

            return response

    def close(self):
        self._request = None

    def read_stream(self, events, count):
        self._log.debug("In read_stream(count = {})".format(count))
        total = 0
        iter_count = 0

        while True:
            n = 0

            iter_count += 1

            self._log.debug("In read_stream(), iteration {}".format(iter_count))

            with self.connect(events) as response:
                self._log.debug("In read_stream(), connected")
                for line in response:
                    data = line.decode('utf-8').strip().split(',')
                    event = {'timestamp': data[0]}
                    for i in range(0, len(events)):
                        event[events[i]] = data[i + 1]

                    yield (event, self)

                    n += 1
                    total += 1

                    self._log.debug("In read_stream(), n = {}, total = {}" \
                                   .format(n, total))

                    if count != 0 and total >= count or not self._request:
                        self._log.debug("In read_stream(), inner break")
                        break

            # If we were closed, stop
            if not self._request:
                self._log.debug("In read_stream(), closed")
                break

            # If the car isn't being driven the streaming server just
            # sends one event and then times out. In that case, stop.
            if n <= 1:
                self._log.debug("In read_stream(), n <= 1")
                break

            # If we got as many or more events than we asked for, stop.
            if count != 0 and total >= count:
                self._log.debug("In read_stream(), done")
                break
