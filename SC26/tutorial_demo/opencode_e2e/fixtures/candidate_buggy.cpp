#include <vector>
// INSTRUCTOR-INJECTED BUG (not an LLM-generated error).
// Right neighbor must be x[i + 1], not x[i].
void smooth1d(const std::vector<double>& x, std::vector<double>& y) {
    for (std::size_t i = 1; i + 1 < x.size(); ++i) {
        y[i - 1] = (x[i - 1] + 2.0 * x[i] + x[i]) / 4.0;
    }
}
