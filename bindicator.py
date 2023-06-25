print("Starting application imports...")

NO_LED = True

from arrow import now as arr_now
import requests, json, time, random

try:
    from rpi_ws281x import PixelStrip, Color
    NO_LED = False
except:
    print("Warning, can't import WS281X lib, in No LED Mode")

import colorsys
import math

print("Starting application...")

led_gamma = [
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,
    1,  1,  1,  1,  1,  1,  1,  1,  1,  2,  2,  2,  2,  2,  2,  2,
    2,  3,  3,  3,  3,  3,  3,  3,  4,  4,  4,  4,  4,  5,  5,  5,
    5,  6,  6,  6,  6,  7,  7,  7,  7,  8,  8,  8,  9,  9,  9, 10,
   10, 10, 11, 11, 11, 12, 12, 13, 13, 13, 14, 14, 15, 15, 16, 16,
   17, 17, 18, 18, 19, 19, 20, 20, 21, 21, 22, 22, 23, 24, 24, 25,
   25, 26, 27, 27, 28, 29, 29, 30, 31, 32, 32, 33, 34, 35, 35, 36,
   37, 38, 39, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 50,
   51, 52, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 66, 67, 68,
   69, 70, 72, 73, 74, 75, 77, 78, 79, 81, 82, 83, 85, 86, 87, 89,
   90, 92, 93, 95, 96, 98, 99,101,102,104,105,107,109,110,112,114,
  115,117,119,120,122,124,126,127,129,131,133,135,137,138,140,142,
  144,146,148,150,152,154,156,158,160,162,164,167,169,171,173,175,
  177,180,182,184,186,189,191,193,196,198,200,203,205,208,210,213,
  215,218,220,223,225,228,231,233,236,239,241,244,247,249,252,255
]

wkdays = [ "MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN" ]

STATE_IDLE = 0
STATE_NO_INTERNET = 1
STATE_GARDEN_WASTE = 2
STATE_GENERAL_WASTE = 3
STATE_RECYCLING = 4

FRAME_TIME = 1.0 / 30.0

entered_state = 0
last_calendar_bin_update = 0
last_bin_light_switch_time = 0
state = STATE_IDLE
cal = None

anim_frame = 0
cal_url = open("url.txt", "r").readlines()[0].strip()

# LED strip configuration:
LED_COUNT = 24        # Number of LED pixels.
LED_PIN = 18          # GPIO pin connected to the pixels (18 uses PWM!).
# LED_PIN = 10        # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53

led_strip = None

SCALE_RED = 1.0
SCALE_GRN = 1.0
SCALE_BLU = 0.82

print("Calender URL is at ", cal_url)

def led_init():
    global led_strip

    if not NO_LED:
        led_strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
        led_strip.begin()

def get_schedule():
    try:
        r = requests.get(cal_url + ("%d" % random.randint(1, 1000)), timeout=5)
    except requests.exceptions:
        print("Timed out requesting data")
        return None
    
    if r.status_code != 200:
        print("Request error (resp %d)" % r.status_code)
        return None
        
    return r.text

def find_nearest_event(c):
    soon_time = None
    soon = None

    now = arr_now().shift(hours=+14)
    print("now+14hrs:", now)

    for event in c.events:
        print(event.begin, event.end, now, event.begin > now, event.end < now)
        if (event.begin < now) and (event.end > now):
            soon = event
            #soon_time = event.begin - now

    return (soon, soon_time)

def lerp_hsv(hsv1, hsv2, f):
    _f = 1 - f
    return ((hsv1[0] * f) + (hsv2[0] * _f), \
            (hsv1[1] * f) + (hsv2[1] * _f), 
            (hsv1[2] * f) + (hsv2[2] * _f))

def wave_colour(hsv1, hsv2, offset):
    global led_strip

    for n in range(LED_COUNT):
        f = (math.sin(((float(n + offset - (LED_COUNT / 2)) / LED_COUNT) * 6.28)) + 1.0) * 0.5
        f = math.pow(f, 10)
        #print(lerp_hsv(hsv1, hsv2, f))
        pix = tuple(map(lambda x: int(x * 255), colorsys.hsv_to_rgb(*lerp_hsv(hsv1, hsv2, f))))
        #print(pix)

        led_strip_gamma(n, pix[0], pix[1], pix[2])

    #rgb1 = colorsys.hsv_to_rgb(*hsv1)
    #rgb2 = colorsys.hsv_to_rgb(*hsv2)

def led_strip_gamma(n, r, g, b):
    global led_strip

    if not NO_LED:
            led_strip.setPixelColorRGB(n, int(led_gamma[r] * SCALE_RED), int(led_gamma[g] * SCALE_GRN), int(led_gamma[b] * SCALE_BLU))

def switch_bin_state(event):
    global state
    print("Got a new event: ", event)

    if event[0] is None:
        print("No event soon, going IDLE")
        state = STATE_IDLE
        return

    nm = event[0].name.strip()
    print("Next event: ", nm)

    # Once we're in a state, we don't change for another 24 hours
    if nm.startswith("Garden"):
        print("Garden waste!")
        state = STATE_GARDEN_WASTE
    elif nm.startswith("Normal"):
        print("General waste!")
        state = STATE_GENERAL_WASTE
    elif nm.startswith("Recycling"):
        print("Recycling!")
        state = STATE_RECYCLING
    else:
        print("Unknown - back to idle!")
        state = STATE_IDLE

def main_loop_iter():
    global last_calendar_bin_update, last_bin_light_switch_time, state, anim_frame, led_strip

    # Do the lightshow
    #state = STATE_GENERAL_WASTE
    #state = STATE_IDLE

    if state == STATE_GARDEN_WASTE:
        h2 = ( 45. / 360., 1.0, 0.2)
        h1 = (100. / 360., 0.8, 0.7)
        wave_colour(h1, h2, (anim_frame / 24))
        if not NO_LED:
            led_strip.show()

        anim_frame += 4.5
        anim_frame %= 1000000
        #anim_frame %= 628

    if state == STATE_GENERAL_WASTE:
        h2 = (270. / 360., 1.0, 0.2)
        h1 = (300. / 360., 0.8, 0.7)
        wave_colour(h1, h2, (anim_frame / 24))
        if not NO_LED:
            led_strip.show()

        anim_frame += 4.5
        anim_frame %= 1000000

    if state == STATE_RECYCLING:
        h2 = (220. / 360., 1.0, 0.2)
        h1 = (180. / 360., 0.8, 0.7)
        wave_colour(h1, h2, (anim_frame / 24))
        if not NO_LED:
            led_strip.show()

        anim_frame += 4.5
        anim_frame %= 1000000

    if state == STATE_NO_INTERNET:
        h2 = (0. / 360., 1.0, 0.2)
        h1 = (0. / 360., 0.5, 0.7)
        wave_colour(h1, h2, (anim_frame / 24))
        if not NO_LED:
            led_strip.show()

        anim_frame += 15.0
        anim_frame %= 1000000

    if state == STATE_IDLE:
        h2 = (0. / 360., 0.0, 0.2)
        h1 = (0. / 360., 0.0, 0.45)
        wave_colour(h1, h2, (anim_frame / 24))
        if not NO_LED:
            led_strip.show()

        anim_frame += 2.0
        anim_frame %= 1000000

    # Normally every 4 hours if idle, the calendar & relevant event is updated.
    # If we lose internet, we retry state every 15 second
    check_rate = 3600 * 4
    if state == STATE_NO_INTERNET:
        check_rate = 15

    if state == STATE_NO_INTERNET or state == STATE_IDLE:
        if (time.time() - last_calendar_bin_update) > check_rate:
            print("Trying to update schedule info...")

        sched = get_schedule()
        if sched == None:
            state = STATE_NO_INTERNET
        else:
            # try to parse the schedule - it's a JSON string
            try:
                print("Pre-JSON text: %s" % sched)
                
                j = json.loads(sched)
                # Types of schedule.  "A" has EVEN weeks with refuse, ODD weeks with recycling;  "B" has the opposite.
                # I live in a "B" area, so this is just based on analysis of public JS.
                week_of_year = datetime.datetime.today().isocalendar()[1]
                weekday = wkdays[datetime.datetime.today().isoweekday()]
                sch = j["schedule"][0]
                sch_weekday = j["day"].upper()
                
                print("JSON: %r" % j)
                print("week_of_year: %d (is_even %d)" % (week_of_year, (week_of_year % 2 == 0)))
                print("weekday: %d" % weekday)
                print("schedule: %d" % sch)
                print("scheduled_weekday: %d" % sch_weekday)
                
                if week_of_year % 2 == 0:
                    # even week of the year
                    if sch == 'A':
                        if weekday == sch_weekday:
                            print("Now STATE_GENERAL_WASTE")
                            state = STATE_GENERAL_WASTE
                        else:
                            print("Now STATE_IDLE")
                            state = STATE_IDLE
                    if sch == 'B':
                        if weekday == sch_weekday:
                            print("Now STATE_RECYCLING")
                            state = STATE_RECYCLING
                        else:
                            print("Now STATE_IDLE")
                            state = STATE_IDLE
                else:
                    # even week of the year
                    if sch == 'A':
                        if weekday == sch_weekday:
                            print("Now STATE_RECYCLING")
                            state = STATE_RECYCLING
                        else:
                            print("Now STATE_IDLE")
                            state = STATE_IDLE
                    if sch == 'B':
                        if weekday == sch_weekday:
                            print("Now STATE_GENERAL_WASTE")
                            state = STATE_GENERAL_WASTE
                        else:
                            print("Now STATE_IDLE")
                            state = STATE_IDLE
            except Exception as e:
                print("JSON parsing error, connection problem, assuming internet issue: %r", e)
                state = STATE_NO_INTERNET

        last_calendar_bin_update = time.time()
    else:
        # If it's been more than 24hr since the bin light switched over then turn it off
        if (last_bin_light_switch_time - time.time()) > 86400:
            state = STATE_IDLE
    
if __name__ == "__main__":
    tl = 0

    # Setup LED strip
    led_init()

    while True:
        main_loop_iter()
        time.sleep(FRAME_TIME)
