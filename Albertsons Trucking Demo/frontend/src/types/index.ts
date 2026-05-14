export interface RouteStop {
  sequence: number;
  location_code: string;
  location_name: string;
  latitude: number;
  longitude: number;
  arrival_minutes_from_start: number;
  departure_minutes_from_start: number;
  weight_delivered_lbs: number;
  cube_delivered: number;
  order_ids: string[];
  on_time: boolean;
}

export interface Route {
  route_id: string;
  trailer_config: string;
  temperature_group: string;
  stops: RouteStop[];
  total_miles: number;
  total_minutes: number;
  total_weight_lbs: number;
  total_cube: number;
  weight_capacity_lbs: number;
  cube_capacity: number;
  weight_utilization: number;
  cube_utilization: number;
  estimated_cost_usd: number;
  on_time: boolean;
  states_traversed: string[];
}

export interface ExceptionItem {
  severity: 'INFO' | 'WARNING' | 'VIOLATION';
  code: string;
  message: string;
  route_id?: string | null;
  location_code?: string | null;
}

export interface NaiveBaseline {
  total_routes: number;
  total_miles: number;
  total_cost_usd: number;
}

export interface SplitFinding {
  location_code: string;
  location_name?: string;
  route_ids: string[];
  total_weight_lbs: number;
  total_cube: number;
  total_cases?: number;
  reason: string;
}

export interface OptimizationResult {
  routes: Route[];
  exceptions: ExceptionItem[];
  considerations: string[];
  relaxed_constraints: string[];
  total_routes: number;
  total_miles: number;
  total_cost_usd: number;
  average_weight_utilization: number;
  average_cube_utilization: number;
  naive_baseline: NaiveBaseline;
  savings_usd: number;
  savings_percent: number;
  solver_status: string;
  solve_seconds: number;
  splits?: SplitFinding[];
}

export interface OptimizeResponse {
  session_id: string;
  distance_source?: string;
  scenario?: string;
  result: OptimizationResult;
}

export interface ChatMessage {
  role: 'user' | 'agent';
  content: string;
}

export interface ScenarioInfo {
  key: string;
  label: string;
  blurb: string;
  highlights: string[];
}
