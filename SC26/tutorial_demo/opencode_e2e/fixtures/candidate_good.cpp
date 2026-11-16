#include <vector>
// Teaching fixture only. The normal /bcp-demo asks OpenCode to generate this.
void smooth1d(const std::vector<double>& x, std::vector<double>& y) {
    for (std::size_t i = 1; i + 1 < x.size(); ++i) {
        y[i - 1] = (x[i - 1] + 2.0 * x[i] + x[i + 1]) / 4.0;
    }
}
