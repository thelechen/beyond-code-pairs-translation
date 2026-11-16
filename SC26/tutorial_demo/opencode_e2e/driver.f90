program run_heat
  implicit none
  integer :: mode, nx, ny, steps, i, j, ios
  real(8) :: alpha, last_max_delta
  real(8), allocatable :: input(:, :), output(:, :)

  read(*, *, iostat=ios) mode, nx, ny, steps, alpha
  if (ios /= 0 .or. (mode /= 1 .and. mode /= 2)) stop 2
  if (nx < 3 .or. nx > 32 .or. ny < 3 .or. ny > 32) stop 3
  if (steps < 0 .or. steps > 50 .or. alpha < 0.0d0 .or. alpha > 0.25d0) stop 4

  allocate(input(nx, ny), output(nx, ny))
  read(*, *, iostat=ios) ((input(i, j), i=1,nx), j=1,ny)
  if (ios /= 0) stop 5

  if (mode == 1) then
    call heat_step_2d(nx, ny, alpha, input, output)
    last_max_delta = 0.0d0
    do j = 2, ny-1
      do i = 2, nx-1
        last_max_delta = max(last_max_delta, abs(output(i, j) - input(i, j)))
      end do
    end do
  else
    call heat_solve_2d(nx, ny, steps, alpha, input, output, last_max_delta)
  end if

  print '(ES24.16E3)', last_max_delta
  do j = 1, ny
    do i = 1, nx
      print '(ES24.16E3)', output(i, j)
    end do
  end do
end program run_heat
