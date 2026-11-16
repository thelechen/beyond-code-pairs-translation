// Trusted driver. The OpenCode Solver creates ONLY smooth1d(), not main().
#include <vector>
#include <iostream>
#include <iomanip>
#include <limits>

void smooth1d(const std::vector<double>& x, std::vector<double>& y);

int main() {
    int n = 0;
    if (!(std::cin >> n) || n < 3 || n > 1024) return 2;
    std::vector<double> x(static_cast<std::size_t>(n));
    std::vector<double> y(static_cast<std::size_t>(n - 2),
                          std::numeric_limits<double>::quiet_NaN());
    for (double& value : x) {
        if (!(std::cin >> value)) return 3;
    }
    smooth1d(x, y);
    std::cout << std::setprecision(17);
    for (double value : y) std::cout << value << '\n';
}
