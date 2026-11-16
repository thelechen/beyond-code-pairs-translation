// Trusted Gate 1 driver: links only heat_step_2d so the Solver can progress.
#include <iomanip>
#include <iostream>
#include <vector>

void heat_step_2d(int nx, int ny, double alpha,
                  const std::vector<double>& input,
                  std::vector<double>& output);

int main() {
    int mode = 0, nx = 0, ny = 0, steps = 0;
    double alpha = 0.0;
    if (!(std::cin >> mode >> nx >> ny >> steps >> alpha)) return 2;
    if (mode != 1 || nx < 3 || nx > 32 || ny < 3 || ny > 32 ||
        alpha < 0.0 || alpha > 0.25) return 3;
    std::vector<double> input(static_cast<std::size_t>(nx * ny));
    std::vector<double> output(input.size());
    for (double& value : input) {
        if (!(std::cin >> value)) return 4;
    }
    heat_step_2d(nx, ny, alpha, input, output);
    double last_max_delta = 0.0;
    for (int j = 1; j < ny - 1; ++j) {
        for (int i = 1; i < nx - 1; ++i) {
            const auto k = static_cast<std::size_t>(i + nx * j);
            const double delta = output[k] - input[k];
            const double magnitude = delta < 0.0 ? -delta : delta;
            if (magnitude > last_max_delta) last_max_delta = magnitude;
        }
    }
    std::cout << std::setprecision(17) << last_max_delta << '\n';
    for (double value : output) std::cout << value << '\n';
}
