import torch
from hypothesis import given
from hypothesis.strategies import integers

from .genmul import logbmm

mint = integers(min_value=6, max_value=10)
lint = integers(min_value=0, max_value=10)
sint = integers(min_value=3, max_value=5)

tmp = torch.rand(10).cuda()
@given(sint, mint, mint, mint)
def test_logbmm(batch, row, inner, col):
    a = torch.rand(batch, row, inner, requires_grad=True).cuda()
    b = torch.rand(batch, inner, col, requires_grad=True).cuda()

    c = (a[:, :, :, None] + b[:, None, :, :]).logsumexp(-2)
    c2 = logbmm(a, b)

    assert(torch.isclose(c, c2).all())

    back = torch.rand(batch, row, col, requires_grad=True).cuda()
    g = torch.autograd.grad(c, (a, b), back, create_graph=True)
    g2 = torch.autograd.grad(c2, (a, b), back, create_graph=True)

    for v1, v2 in zip(g, g2):
        assert (torch.isclose(v1, v2).all())


    back2 = (torch.rand(batch, row, inner).cuda(),
             torch.rand(batch, inner, col).cuda())

    c = (a[:, :, :, None] + b[:, None, :, :]).logsumexp(-2)
    g = torch.autograd.grad(c, (a, b), back, create_graph=True)
    h = torch.autograd.grad((g[0], g[1]), (a, b, back), back2)

    c2 = logbmm(a, b)
    g2 = torch.autograd.grad(c2, (a, b), back, create_graph=True)
    h2 = torch.autograd.grad((g2[0], g2[1]), (a, b, back), back2)

    for i, (v1, v2) in enumerate(zip(h, h2)):
        assert torch.isclose(v1, v2, 1e-2).all(), "Round: " + str(i)


from .sparse import banddiag, BandedMatrix, BandedLogMul
def bmm(a, b):
    return b.multiply_log(a.transpose())
def bmm_simple(a, b):
    return b.multiply_log_simple(a.transpose())



@given(sint, mint, mint, mint)
def test_sparse_nonzero(batch, n, lu, ld):
    start = torch.rand(batch, n, n).cuda()
    band, _ = banddiag(start, lu, ld)
    band.requires_grad_(True)

    start2 = torch.rand(batch, n, n).cuda()
    band2, _ = banddiag(start2, lu, ld)
    band2.requires_grad_(True)


    a = BandedLogMul.apply(band, lu, ld, band2, lu, ld, lu+ld, ld+lu)

    back = torch.rand(a.shape, requires_grad=True).cuda()
    g = torch.autograd.grad(a, (band), back, create_graph=True)

    back2 = (torch.rand(g[0].shape).cuda(),
             torch.rand(g[1].shape).cuda())

    h = torch.autograd.grad((g[0]), (band),
                            (back2[0], back2[1]))
    print(h[0])
    print(h[1])
    print(h[2])
    assert(False)

@given(sint, mint, mint, mint)
def test_sparse(batch, n, lu, ld):
    start = torch.rand(batch, n, n, requires_grad=True)
    band, _ = banddiag(start, lu, ld)
    banded_x = BandedMatrix(band, lu, ld)
    banded_x_cuda = BandedMatrix(band.cuda(), lu, ld)
    x = banded_x.to_dense()

    start2 = torch.rand(batch, n, n, requires_grad=True)
    band, _ = banddiag(start2, lu, ld)
    banded_y = BandedMatrix(band, lu, ld)
    banded_y_cuda = BandedMatrix(band.cuda(), lu, ld)
    y = banded_y.to_dense()


    a = bmm(banded_x_cuda, banded_y_cuda).data
    b = bmm_simple(banded_x, banded_y).data
    assert torch.isclose(a.cpu(), b).all()

    back = torch.rand(a.shape, requires_grad=True)
    g = torch.autograd.grad(a, (start, start2), back.cuda(), create_graph=True)
    g2 = torch.autograd.grad(b, (start, start2), back, create_graph=True)

    for v1, v2 in zip(g, g2):
        assert torch.isclose(v1.cpu(), v2).all()

    back2 = (torch.rand(g[0].shape),
             torch.rand(g[1].shape))

    h2 = torch.autograd.grad((g2[0], g2[1]), (back, start, start2), (back2[0], back2[1]))

    print("here")
    h = torch.autograd.grad((g[0].cuda(), g[1].cuda()), (back, start, start2),
                            (back2[0].cuda(), back2[1].cuda()))
    for i, (v1, v2) in enumerate(zip(h, h2)):
        print(i)
        print(v1.shape)
        print(v2.shape)
        print(v1)
        print(v2)

        assert torch.isclose(v1, v2, 1e-2).all(), "Round: " + str(i)
