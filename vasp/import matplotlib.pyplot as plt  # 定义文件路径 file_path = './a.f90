implicit none
integer :: ArgNum,i,j,k
character(len=20) :: filename,str1
integer :: Nind,AtomNum,FrameNum,Nline

real,dimension(3,3)::Lattice

real,dimension(:,:,:),allocatable :: xyz
real,dimension(:),allocatable   :: msd
real,dimension(:,:),allocatable :: msd_i
character(2) :: temp
integer :: stat1

ArgNum=command_argument_count()
if(ArgNum/=2) then
   write(*,*) "Wrong input argument!"
   stop
end if
call get_command_argument(1,filename)
filename=trim(adjustl(filename))
call get_command_argument(2,str1)
read(str1,*) Nind

open(unit=111,file=filename,status='old')

read(111,*) AtomNum
Nline=1
do
  read(111,*,iostat=stat1)
  Nline=Nline+1
  if(stat1/=0) exit
end do
FrameNum=Nline/(AtomNum+2)
write(*,*) AtomNum,FrameNum
allocate(xyz(FrameNum,AtomNum,3))

rewind(111)
do i=1,FrameNum
  read(111,*)
  read(111,*)
  do j=1,AtomNum
    read(111,*) temp, xyz(i,j,:)
  end do
end do
close(111)

allocate(msd(FrameNum),msd_i(FrameNum,3))
if(Nind==0) then
   call system("mkdir msd_all")
   do i=1,AtomNum
       call get_msd_ind(i,pre="msd_all/")
   end do
else
   if(Nind>AtomNum) then
       write(*,*) "Error! Nind>AtomNum"
       stop
   end if
   call get_msd_ind(Nind)
end if

contains
subroutine get_msd_ind(ind,pre)
implicit none
integer,intent(in) :: ind
character(*),optional,intent(in)  :: pre
character(20) :: outname
integer :: del_t,n,m,Fd
write(outname,*) ind
if(present(pre)) then
    outname=pre//trim(adjustl(outname))
else
    outname=trim(adjustl(outname))
end if
write(*,*) "Dealing with "//outname//".msd"
write(*,*) ind
msd=0
msd_i=0
do del_t=1,FrameNum-1
  Fd=FrameNum-del_t
  if(mod(del_t,100)==0) write(*,*) del_t
  do n=1,Fd
    do m=1,3
        msd_i(del_t,m)=msd_i(del_t,m)+((xyz(n+del_t,ind,m)-xyz(n,ind,m))**2)/Fd
    end do
  end do
  do m=1,3
      msd(del_t)=msd(del_t)+msd_i(del_t,m)
  end do
end do
open(99,file=trim(adjustl(outname))//".msd",status="replace")
open(98,file=trim(adjustl(outname))//".msd_i",status="replace")
do del_t=1,framenum-1
    write(99,*) msd(del_t)
    write(98,*) msd_i(del_t,:)
end do
close(99)
close(98)
end subroutine
end program
