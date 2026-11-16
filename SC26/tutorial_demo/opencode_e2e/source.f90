! A tiny 1-D three-point stencil. This is the *implementation* only;
! the Questioner requests a deterministic, self-checking test program.
subroutine smooth1d(n, x, y)
  implicit none
  integer, intent(in) :: n
  real(8), intent(in) :: x(n)
  real(8), intent(out) :: y(n-2)
  integer :: i
  do i = 2, n-1
    y(i-1) = (x(i-1) + 2.0d0*x(i) + x(i+1)) / 4.0d0
  end do
end subroutine smooth1d
