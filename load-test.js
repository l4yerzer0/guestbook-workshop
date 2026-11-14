import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '5s', target: 20 },
    { duration: '30s', target: 20 },
    { duration: '5s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8000';

export default function () {
  const res = http.get(`${BASE_URL}/messages`);
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
  sleep(0.1);
}
