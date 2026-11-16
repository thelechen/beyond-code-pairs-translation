! Two-dimensional heat diffusion used by the SC26 progressive translation demo.
! Arrays are stored in Fortran column-major order.  In a flat C++ vector the
! matching zero-based offset is i + nx*j.
subroutine heat_step_2d(nx, ny, alpha, input, output)
  implicit none
  integer, intent(in) :: nx, ny
  real(8), intent(in) :: alpha
  real(8), intent(in) :: input(nx, ny)
  real(8), intent(out) :: output(nx, ny)
  integer :: i, j

  ! Copying first deliberately preserves all four boundaries.
  output = input
  do j = 2, ny-1
    do i = 2, nx-1
      output(i, j) = input(i, j) + alpha * ( &
          input(i-1, j) + input(i+1, j) + &
          input(i, j-1) + input(i, j+1) - 4.0d0*input(i, j))
    end do
  end do
end subroutine heat_step_2d

subroutine heat_solve_2d(nx, ny, steps, alpha, input, output, last_max_delta)
  implicit none
  integer, intent(in) :: nx, ny, steps
  real(8), intent(in) :: alpha
  real(8), intent(in) :: input(nx, ny)
  real(8), intent(out) :: output(nx, ny), last_max_delta
  real(8), allocatable :: current(:, :), next_grid(:, :)
  integer :: i, j, step

  allocate(current(nx, ny), next_grid(nx, ny))
  current = input
  last_max_delta = 0.0d0

  do step = 1, steps
    call heat_step_2d(nx, ny, alpha, current, next_grid)
    last_max_delta = 0.0d0
    do j = 2, ny-1
      do i = 2, nx-1
        last_max_delta = max(last_max_delta, abs(next_grid(i, j) - current(i, j)))
      end do
    end do
    current = next_grid
  end do

  output = current
  deallocate(current, next_grid)
end subroutine heat_solve_2d
