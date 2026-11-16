program run_stencil
  implicit none
  integer :: n, i, ios
  real(8), allocatable :: x(:), y(:)

  read(*, *, iostat=ios) n
  if (ios /= 0 .or. n < 3 .or. n > 1024) stop 2
  allocate(x(n), y(n-2))
  read(*, *, iostat=ios) x
  if (ios /= 0) stop 3
  call smooth1d(n, x, y)
  do i = 1, n-2
    print '(ES24.16E3)', y(i)
  end do
end program run_stencil
