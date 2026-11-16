#include <algorithm>
#include <cmath>
#include <vector>

void heat_step_2d(int nx, int ny, double alpha,
                  const std::vector<double>& input,
                  std::vector<double>& output) {
    output = input;
    for (int j = 1; j < ny - 1; ++j) {
        for (int i = 1; i < nx - 1; ++i) {
            const auto k = static_cast<std::size_t>(i + nx * j);
            output[k] = input[k] + alpha *
                (input[k - 1] + input[k + 1] + input[k - nx] + input[k + nx]
                 - 4.0 * input[k]);
        }
    }
}

// INSTRUCTOR-INJECTED BUG: after swap, next_grid is the stale previous state.
void heat_solve_2d(int nx, int ny, int steps, double alpha,
                   const std::vector<double>& input,
                   std::vector<double>& output,
                   double& last_max_delta) {
    std::vector<double> current = input;
    std::vector<double> next_grid(input.size());
    last_max_delta = 0.0;
    for (int step = 0; step < steps; ++step) {
        heat_step_2d(nx, ny, alpha, current, next_grid);
        last_max_delta = 0.0;
        for (int j = 1; j < ny - 1; ++j) {
            for (int i = 1; i < nx - 1; ++i) {
                const auto k = static_cast<std::size_t>(i + nx * j);
                last_max_delta = std::max(last_max_delta,
                    std::abs(next_grid[k] - current[k]));
            }
        }
        current.swap(next_grid);
    }
    output = steps == 0 ? current : next_grid;
}
