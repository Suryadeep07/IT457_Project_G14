import http from 'k6/http';
import { check } from 'k6';

const TARGET = __ENV.TARGET;
const PEAK = Number(__ENV.PEAK_RPS || 60);
const BASE = Number(__ENV.BASE_RPS || 5);
const WORK = __ENV.WORK || '200000';
const SCALE = Number(__ENV.TIME_SCALE || 1);
const QUIET = Number(__ENV.QUIET_SEC || 1200);
const MODE = __ENV.MODE || 'holiday';
const ENDPOINT = __ENV.ENDPOINT || '/work';

const dur = (s) => `${Math.max(1, Math.round(s * SCALE))}s`;

const holidayStages = [
  { target: BASE, duration: dur(120) },
  { target: PEAK, duration: dur(300) },
  { target: PEAK, duration: dur(600) },
  { target: BASE, duration: dur(60) },
  { target: BASE, duration: dur(QUIET) },
];

const calibrateStages = [10, 20, 40, 60, 80, 100, 120].flatMap((r) => [
  { target: r, duration: '10s' },
  { target: r, duration: '50s' },
]);

export const options = {
  scenarios: {
    traffic: {
      executor: 'ramping-arrival-rate',
      startRate: BASE,
      timeUnit: '1s',
      preAllocatedVUs: 100,
      maxVUs: 2000,
      stages: MODE === 'calibrate' ? calibrateStages : holidayStages,
    },
  },
};

export default function () {
  const res = http.get(`${TARGET}${ENDPOINT}?n=${WORK}`, { timeout: '10s' });
  check(res, { 'status is 200': (r) => r.status === 200 });
}